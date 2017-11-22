# coding: utf-8

__all__ = ['SingleFrameFakeClient']

import os.path
import time
import timeit

from .comms import Client, ClockSynchronizer, Connection
from .logging import Logger
from .protocol import MessageId, deserialize, deserialize_header, serialize


class FakeConnection(Connection):

    """Fake connection which "receives" packets from a list."""

    def __init__(self, packets=None, repeat=False, rate=None):
        """
        Args:
            packets (list): Packets (from first to last)
            repeat (bool): When the end of the list is reached, either (true) loop back to the start
                or (false) raise SystemExit
            rate (int): If provided, "receive" mocap frame packets at this rate in Hz and timestamp
                packets with the current time, otherwise "receive" packets as fast as possible and
                timestamp with zero
        """
        super(FakeConnection, self).__init__(command_socket=None, data_socket=None, command_address=None)
        self.packets = packets or []
        self.repeat = repeat
        self.i = 0
        self.rate = rate
        self.last_frame_time = None

    @property
    def packets_remaining(self):
        return len(self.packets) - self.i

    def add_packet(self, packet, received_time=None):
        self.packets.append(packet)
        if received_time is not None:
            self.received_times.append(received_time)

    def add_message(self, message, received_time=None):
        self.add_packet(serialize(message), received_time)

    def wait_for_packet_raw(self, timeout=None):
        if self.i >= len(self.packets):
            # Hit end of list
            if self.repeat:
                self.i = 0
            else:
                raise SystemExit
        packet = self.packets[self.i]
        self.i += 1

        received_time = 0
        if self.rate:
            message_id, _ = deserialize_header(packet)
            if message_id == MessageId.FrameOfData:
                if self.last_frame_time:
                    next_frame_due = self.last_frame_time + 1.0/self.rate
                    sleep_time = next_frame_due - timeit.default_timer()
                    time.sleep(max(sleep_time, 0))
                self.last_frame_time = timeit.default_timer()
            received_time = self.last_frame_time

        return packet, received_time

    def send_packet(self, *args, **kwargs):
        pass

    def bind_data_socket(self, *args, **kwargs):
        pass


class FakeClockSynchronizer(ClockSynchronizer):

    """Fake clock synchronizer that pretends any time it's asked about it is the current time."""

    def update(self, *args, **kwargs):
        # Don't send any packets
        pass

    def server_to_local_time(self, server_ticks):
        return timeit.default_timer()

    def initial_sync(self, *args, **kwargs):
        pass


class SingleFrameFakeClient(Client):

    """Fake NatNet client that just returns the same pre-recorded mocap frame packet repeatedly."""

    @classmethod
    def fake_connect(cls, rate=None, logger=Logger(),
                     test_data_folder='test_data',
                     frame_packet_filename='mocapframe_packet_v3.bin',
                     serverinfo_packet_filename='serverinfo_packet_v3.bin',
                     modeldef_packet_filename='modeldef_packet_v3.bin'):
        frame_packet = open(os.path.join(test_data_folder, frame_packet_filename), 'rb').read()
        server_info_packet = open(os.path.join(test_data_folder, serverinfo_packet_filename), 'rb').read()
        model_definitions_packet = open(os.path.join(test_data_folder, modeldef_packet_filename), 'rb').read()
        conn = FakeConnection([frame_packet], repeat=True, rate=rate)
        clock_synchronizer = FakeClockSynchronizer(deserialize(server_info_packet), logger)
        inst = cls(conn, clock_synchronizer, logger)
        inst._handle_model_definitions(deserialize(model_definitions_packet))
        return inst
