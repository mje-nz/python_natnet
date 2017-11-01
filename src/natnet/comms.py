# coding: utf-8

import select
import socket
import struct
import timeit

import attr

from . import protocol
from .protocol.MocapFrameMessage import LabelledMarker, RigidBody, TimingInfo  # noqa: F401


@attr.s
class Connection(object):

    _command_socket = attr.ib()
    _data_socket = attr.ib()
    _command_address = attr.ib()

    def bind_data_socket(self, multicast_addr, data_port):
        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(multicast_addr), socket.INADDR_ANY)
        self._data_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # Bind to data port
        self._data_socket.bind(('', data_port))

    @classmethod
    def open(cls, server_ip, command_port=1510, multicast_addr=None, data_port=None):
        # Create command socket and bind to any address
        command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        command_socket.bind(('', 0))
        command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Create data socket
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        inst = cls(command_socket, data_socket, (server_ip, command_port))

        if multicast_addr is not None and data_port is not None:
            inst.bind_data_socket(multicast_addr, data_port)
            # Otherwise, use a Connect message and get these from the ServerInfo response

        return inst

    def __del__(self):
        if self._command_socket:
            self._command_socket.close()
            self._command_socket = None
        if self._data_socket:
            self._data_socket.close()
            self._data_socket = None

    def wait_for_packet(self, timeout=None):
        """Return the next packet to arrive on either socket, or None if a timeout occurred.

        :param timeout: Timeout in seconds
        :type timeout: float
        """
        sockets = [self._command_socket, self._data_socket]
        readable, _, exceptional = select.select(sockets, [], sockets, timeout)

        for s in exceptional:
            which = 'command' if s is self._command_socket else 'data'
            raise IOError('Something went wrong with the', which, 'socket')

        data = None
        received_time = None
        if len(readable) > 0:
            # Just get the first message this time around
            data, address = readable[0].recvfrom(32768)  # type: bytes
            received_time = timeit.default_timer()  # type: float

        return data, received_time

    def wait_for_packet_with_id(self, id_):
        """Return the next packet with the given ID, discarding any others."""
        # TODO: There's probably a better way of doing this, but it'll do until I implement the rest
        while True:
            packet, received_time = self.wait_for_packet()
            received_id, = protocol.uint16_t.unpack(packet[:2])
            if received_id == id_:
                return packet, received_time

    def send_packet(self, packet):
        self._command_socket.sendto(packet, self._command_address)


@attr.s
class TimestampAndLatency(object):

    # Camera mid-exposure timestamp (from local clock, *not* server clock)
    timestamp = attr.ib()  # type: float

    # Time from camera mid-exposure to Motive transmitting frame
    system_latency = attr.ib()  # type: float

    # Time from transmitting frame to receiving frame
    transit_latency = attr.ib()  # type: float

    # Time from receiving frame to calling callback
    processing_latency = attr.ib()  # type: float

    @classmethod
    def calculate(cls, received_timestamp, timing_info, server_info):
        """Calculate latencies and local timestamp.

        :type received_timestamp: float
        :type timing_info: TimingInfo
        :type server_info: protocol.ServerInfoMessage"""

        system_latency_ticks = timing_info.transmit_timestamp - timing_info.camera_mid_exposure_timestamp
        system_latency = float(system_latency_ticks)/server_info.high_resolution_clock_frequency
        transit_latency = 0.7e-3  # Just hard-code this for now
        # For now, just work backwards from the received timestamp
        timestamp = received_timestamp - system_latency - transit_latency
        processing_latency = timeit.default_timer() - received_timestamp
        return cls(timestamp, system_latency, transit_latency, processing_latency)

    @property
    def latency(self):
        """Time from camera mid-exposure to calling callback ."""
        return self.system_latency + self.transit_latency + self.processing_latency


@attr.s
class Client(object):

    _conn = attr.ib()  # type: Connection
    _server_info = attr.ib()  # type: protocol.ServerInfoMessage
    _callback = attr.ib(None)

    @classmethod
    def connect(cls, server_ip):
        print('Connecting to', server_ip)
        conn = Connection.open(server_ip)
        print('Getting server info')
        conn.send_packet(protocol.serialize(protocol.ConnectMessage()))
        server_info_packet, received_time = conn.wait_for_packet_with_id(protocol.MessageId.ServerInfo)
        server_info = protocol.deserialize(server_info_packet)  # type: protocol.ServerInfoMessage
        print('Server application:', server_info.app_name)
        print('Server version:', server_info.app_version)
        assert server_info.connection_info.multicast
        conn.bind_data_socket(server_info.connection_info.multicast_address,
                              server_info.connection_info.data_port)
        print('Ready')
        return cls(conn, server_info)

    def set_callback(self, callback):
        """Set the frame callback.

        :type callback: (list[RigidBody], list[LabelledMarker], TimingAndLatency) -> None"""
        self._callback = callback

    def spin(self):
        """Receive messages and dispatch to handlers."""
        try:
            while True:
                packet, received_time = self._conn.wait_for_packet()
                message_id, payload_data = protocol.deserialize_header(packet)
                if message_id == protocol.MessageId.FrameOfData:
                    if self._callback:
                        frame = protocol.deserialize_payload(message_id, payload_data)
                        rigid_bodies = frame.rigid_bodies
                        labelled_markers = frame.labelled_markers
                        timestamp_and_latency = TimestampAndLatency.calculate(
                            received_time, frame.timing_info, self._server_info)
                        self._callback(rigid_bodies, labelled_markers, timestamp_and_latency)
                else:
                    print('Unhandled message type:', message_id.name)
        except (KeyboardInterrupt, SystemExit):
            print('Exiting')
