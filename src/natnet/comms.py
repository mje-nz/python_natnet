# coding: utf-8
"""Communications.

Note that all local timestamps (e.g. packet reception time) are from :func:`timeit.default_timer`.
"""

from __future__ import print_function

import select
import socket
import struct
import timeit

import attr

from . import protocol
from .protocol.ModelDefinitionsMessage import RigidBodyDescription

__all__ = ['Client', 'Connection', 'TimestampAndLatency']


@attr.s
class Connection(object):

    """Connection to NatNet server."""

    _command_socket = attr.ib()  # type: socket.socket
    _data_socket = attr.ib()  # type: socket.socket
    _command_address = attr.ib()  # type: tuple[str, int]

    def bind_data_socket(self, multicast_addr, data_port):
        """Bind data socket and begin receiving mocap frames.

        Args:
            multicast_addr (str): Server's IPv4 multicast address
            data_port (int): Server's data port
        """
        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(multicast_addr), socket.INADDR_ANY)
        self._data_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        # Bind to data port
        self._data_socket.bind(('', data_port))

    @classmethod
    def open(cls, server, command_port=1510, multicast_addr=None, data_port=None):
        """Open a connection to a NatNet server.

        If you don't know the multicast address and data port, you can get them from a ServerInfo
        message (by sending a Connect message and waiting) then open the data socket later with
        :func:`bind_data_socket`.

        Args:
            server (str): IPv4 address of server (hostname probably works too)
            command_port (int): Server's command port
            multicast_addr (str): Server's IPv4 multicast address
            data_port (int): Server's data port
        """
        # Create command socket and bind to any address
        command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        command_socket.bind(('', 0))
        command_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Create data socket
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        inst = cls(command_socket, data_socket, (server, command_port))

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

    def wait_for_packet_raw(self, timeout=None):
        """Return the next packet to arrive on either socket as raw bytes.

        Args:
            timeout (float): Timeout in seconds

        Returns:
            tuple[bytes, float]: Raw packet and received timestamp, or (None, None) if a timeout
            occurred
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

    def wait_for_packet(self, timeout=None):
        """Return the next packet to arrive, deserializing the header but not the payload.

        If `timeout` is given and no packet is received within that time, return (None, None, None).

        Returns:
            tuple[MessageId, bytes, float]:
        """
        packet, received_time = self.wait_for_packet_raw(timeout)
        message_id, payload = protocol.deserialize_header(packet) if packet is not None else (None, None)
        return message_id, payload, received_time

    def wait_for_message(self, timeout=None):
        """Return the next message to arrive on either socket, or None if a timeout occurred."""
        packet, received_time = self.wait_for_packet_raw(timeout)
        message = protocol.deserialize(packet) if packet is not None else None
        return message, received_time

    def wait_for_message_with_id(self, id_, timeout=None):
        """Return the next message received of the given type, discarding any others."""
        # TODO: There's probably a better way of doing this (that doesn't throw away other packets)
        #       but it can wait until I see if that matters
        while True:
            message_id, payload, received_time = self.wait_for_packet(timeout)
            if message_id == id_:
                return protocol.deserialize_payload(message_id, payload), received_time

    def send_packet(self, packet):
        self._command_socket.sendto(packet, self._command_address)

    def send_message(self, message):
        self.send_packet(protocol.serialize(message))


@attr.s
class ClockSynchronizer(object):

    """Synchronize clocks with a NatNet server using Cristian's algorithm."""

    _server_info = attr.ib()
    _last_server_time = attr.ib(None)
    _last_synced_at = attr.ib(None)
    _min_rtt = attr.ib(1e-3)
    _echo_count = attr.ib(0)
    _last_sent_time = attr.ib(None)
    _skew = attr.ib(0)

    def initial_sync(self, conn):
        """Use a series of echoes to measure minimum round trip time.

        Args:
            conn (:class:`Connection`):
        """
        while self._echo_count < 100:
            self.send_echo_request(conn)
            response, received_time = conn.wait_for_message_with_id(protocol.MessageId.EchoResponse,
                                                                    timeout=0.1)
            if response is None:
                print('Timeout out while waiting for echo response {}'.format(self._echo_count + 1))
            self.handle_echo_response(response, received_time)

    def server_ticks_to_seconds(self, server_ticks):
        return float(server_ticks)/self._server_info.high_resolution_clock_frequency

    def server_to_local_time(self, server_ticks):
        """Convert a NatNet HPC timestamp to local time (according to timeit.default_timer)."""
        server_time = self.server_ticks_to_seconds(server_ticks)
        server_time_since_last_sync = server_time - self._last_server_time
        local_time = self._last_synced_at + server_time_since_last_sync*(1 + self._skew)
        return local_time

    def local_to_server_time(self, local_time):
        local_time_since_last_sync = local_time - self._last_synced_at
        server_time = self._last_server_time + local_time_since_last_sync*(1 + self._skew)
        return server_time

    def server_time_now(self):
        """Get the current time on the server's HPC."""
        return self.local_to_server_time(timeit.default_timer())

    def send_echo_request(self, conn):
        self._last_sent_time = timeit.default_timer()
        sent_timestamp_int = int(self._last_sent_time*1e9)
        conn.send_message(protocol.EchoRequestMessage(sent_timestamp_int))

    def handle_echo_response(self, response, received_time):
        assert response.request_timestamp == int(self._last_sent_time*1e9)
        rtt = received_time - self._last_sent_time
        server_reception_time = self.server_ticks_to_seconds(response.received_timestamp)
        if self._last_server_time is None:
            # First echo, initialize
            self._last_server_time = server_reception_time + rtt/2
            self._last_synced_at = received_time
            print('First echo: RTT {:.2f}ms, server time {:.1f}'.format(1000*rtt, self._last_server_time))
        else:
            # The true server time falls within server_reception_time +- (rtt - true_min_rtt)/2.
            # We'd generally like to be within 0.1ms of the actual time, which would require the RTT
            # to be less than 0.1ms over the minimum RTT.  However, I've measured clock skew of
            # 0.03ms/s before, so if we start with a perfect estimate and don't sync for 5 seconds we
            # could already be out by 0.1ms.  Therefore our threshold should start at 0.05ms and
            # increase over time such that it's always a bit less than our potential accumulated
            # drift.
            # TODO: Kalman filter
            dt = received_time - self._last_synced_at
            accumulated_drift = dt*0.05e-3  # Assume skew is severe and we have a bad estimate of it
            rtt_threshold = self._min_rtt + max(0.05e-3, max(0.1e-3, accumulated_drift))
            if rtt < rtt_threshold:
                old_server_time_when_received = self.local_to_server_time(received_time)
                self._last_server_time = server_reception_time + rtt/2
                self._last_synced_at = received_time
                correction = self._last_server_time - old_server_time_when_received
                drift = correction/dt
                # This only works over a reasonably long time period
                if dt > 1:
                    if self._skew == 0:
                        # Initialize
                        self._skew = -drift
                    else:
                        # Slowly converge on the true skew
                        self._skew += drift/2
                print(
                    'Echo {: 5d}: RTT {:.2f}ms (min {:.2f}ms), server time {:.1f}s, dt {: .3f}s, '
                    'correction {: .3f}ms, drift {:7.3f}ms/s, new skew: {: .3f}ms/s'
                    .format(self._echo_count, 1000*rtt, 1000*self._min_rtt, self._last_server_time,
                            dt, 1000*correction, 1000*drift, 1000*self._skew))

        if rtt < self._min_rtt:
            self._min_rtt = rtt
        self._echo_count += 1

    def update(self, conn):
        now = timeit.default_timer()
        time_since_last_echo = now - self._last_sent_time
        time_since_last_sync = now - self._last_synced_at

        minimum_time_between_echo_requests = 0.5
        if time_since_last_sync > 5:
            minimum_time_between_echo_requests = 0.1
        if time_since_last_sync > 10:
            minimum_time_between_echo_requests = 0.01
        if time_since_last_echo > minimum_time_between_echo_requests:
            self.send_echo_request(conn)


@attr.s
class TimestampAndLatency(object):

    """Timing information for a received mocap frame.

    Attributes:
        timestamp (float): Camera mid-exposure timestamp (according to local clock)
        system_latency (float): Time from camera mid-exposure to Motive transmitting frame
        transit_latency (float): Time from transmitting frame to receiving frame
        processing_latency (float): Time from receiving frame to calling callback
    """

    timestamp = attr.ib()  # type: float
    system_latency = attr.ib()  # type: float
    transit_latency = attr.ib()  # type: float
    processing_latency = attr.ib()  # type: float

    @classmethod
    def _calculate(cls, received_timestamp, timing_info, clock):
        """Calculate latencies and local timestamp.

        Args:
            received_timestamp (float):
            timing_info (:class:`~protocol.MocapFrameMessage.TimingInfo`):
            clock (:class:`ClockSynchronizer`):
        """
        timestamp = clock.server_to_local_time(timing_info.camera_mid_exposure_timestamp)
        system_latency_ticks = timing_info.transmit_timestamp - timing_info.camera_mid_exposure_timestamp
        system_latency = clock.server_ticks_to_seconds(system_latency_ticks)
        transit_latency = received_timestamp - clock.server_to_local_time(timing_info.transmit_timestamp)
        processing_latency = timeit.default_timer() - received_timestamp
        return cls(timestamp, system_latency, transit_latency, processing_latency)

    @property
    def latency(self):
        """Time from camera mid-exposure to calling callback."""
        return self.system_latency + self.transit_latency + self.processing_latency


@attr.s
class Client(object):

    """NatNet client.

    This class connects to a NatNet server and calls a callback whenever a frame of mocap data
    arrives.
    """

    _conn = attr.ib()  # type: Connection
    _clock_synchronizer = attr.ib()  # type: ClockSynchronizer
    rigid_body_names = attr.ib(attr.Factory(dict))  # type: dict[int, str]
    _callback = attr.ib(None)

    @classmethod
    def connect(cls, server):
        """Connect to a NatNet server.

        Args:
            server (str): IPv4 address of server (hostname probably works too)
        """
        print('Connecting to', server)
        conn = Connection.open(server)

        print('Getting server info')
        conn.send_message(protocol.ConnectMessage())
        server_info, received_time = conn.wait_for_message_with_id(protocol.MessageId.ServerInfo)
        print('Server application:', server_info.app_name)
        print('Server version:', server_info.app_version)
        assert server_info.connection_info.multicast
        conn.bind_data_socket(server_info.connection_info.multicast_address,
                              server_info.connection_info.data_port)

        print('Synchronizing clocks')
        clock_synchronizer = ClockSynchronizer(server_info)
        clock_synchronizer.initial_sync(conn)
        inst = cls(conn, clock_synchronizer)

        print('Getting data descriptions')
        conn.send_message(protocol.RequestModelDefinitionsMessage())
        model_definitions_message, _ = conn.wait_for_message_with_id(protocol.MessageId.ModelDef)
        inst._handle_model_definitions(model_definitions_message)

        print('Ready')
        return inst

    def set_callback(self, callback):
        """Set the frame callback.

        It will be called with a list of :class:`~natnet.protocol.MocapFrameMessage.RigidBody`, a list of
        :class:`~natnet.protocol.MocapFrameMessage.LabelledMarker`, and a :class:`TimestampAndLatency`.
        """
        self._callback = callback

    def _handle_model_definitions(self, model_definitions_message):
        """Update local list of rigid body id:name mappings.

        :type model_definitions_message: protocol.ModelDefinitionsMessage
        """
        models = model_definitions_message.models
        rigid_body_descriptions = [m for m in models if type(m) is RigidBodyDescription]
        self.rigid_body_names = {m.id_: m.name for m in rigid_body_descriptions}
        print('Rigid body names:', self.rigid_body_names)
        if len(rigid_body_descriptions) > len(self.rigid_body_names):
            names = [m.name for m in rigid_body_descriptions]
            missing_bodies = [n for n in names if n not in self.rigid_body_names.values()]
            print('Warning: duplicate streaming IDs detected (ignoring {})'
                  .format(', '.join(repr(m) for m in missing_bodies)))

    def run_once(self, timeout=None):
        """Receive and process one message."""
        message_id, payload, received_time = self._conn.wait_for_packet(timeout)
        if message_id is None:
            print('Timed out waiting for packet')
            return
        if message_id == protocol.MessageId.FrameOfData:
            if self._callback:
                frame = protocol.deserialize_payload(message_id, payload)
                rigid_bodies = frame.rigid_bodies
                labelled_markers = frame.labelled_markers
                timestamp_and_latency = TimestampAndLatency._calculate(
                    received_time, frame.timing_info, self._clock_synchronizer)
                self._callback(rigid_bodies, labelled_markers, timestamp_and_latency)

                if frame.tracked_models_changed:
                    print('Tracked models have changed, requesting new model definitions')
                    self._conn.send_packet(protocol.serialize(
                        protocol.RequestModelDefinitionsMessage()))
        elif message_id == protocol.MessageId.ModelDef:
            model_definitions_message = protocol.deserialize_payload(message_id, payload)
            self._handle_model_definitions(model_definitions_message)
        elif message_id == protocol.MessageId.EchoResponse:
            echo_response_message = protocol.deserialize_payload(message_id, payload)
            self._clock_synchronizer.handle_echo_response(echo_response_message, received_time)
        else:
            print('Unhandled message type:', message_id.name)
        self._clock_synchronizer.update(self._conn)

    def spin(self, timeout=None):
        """Continuously receive and process messages."""
        try:
            while True:
                self.run_once(timeout)
        except (KeyboardInterrupt, SystemExit):
            print('Exiting')
