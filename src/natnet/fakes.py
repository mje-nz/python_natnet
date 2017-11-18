# coding: utf-8

__all__ = ['SingleFrameFakeClient']

import os.path

from .comms import Client, ClockSynchronizer, Connection
from .protocol import deserialize, serialize


class FakeConnection(Connection):

    """Fake connection which "receives" packets from a list.

    Received times are optional; 0 will be used if not provided.
    """

    def __init__(self, packets=None, received_times=None, repeat=False):
        """
        Args:
            packets (list): Packets (from first to last)
            received_times (list): Received times
            repeat (bool): When the end of the list is reached, either (true) loop back to the start or (false) raise
                SystemExit
        """
        super(FakeConnection, self).__init__(command_socket=None, data_socket=None, command_address=None)
        self.packets = packets or []
        self.received_times = received_times or []
        self.repeat = repeat
        self.i = 0

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
        if self.received_times:
            received_time = self.received_times[self.i]
        else:
            received_time = 0
        self.i += 1
        return packet, received_time

    def send_packet(self, *args, **kwargs):
        pass

    def bind_data_socket(self, *args, **kwargs):
        pass


class FakeClockSynchronizer(ClockSynchronizer):

    """Fake clock synchronizer that pretends the local clock is the same as the server clock."""

    def update(self, *args, **kwargs):
        # Don't send any packets
        pass

    def server_to_local_time(self, server_ticks):
        return self.server_ticks_to_seconds(server_ticks)

    def initial_sync(self, *args, **kwargs):
        pass


class SingleFrameFakeClient(Client):

    """Fake NatNet client that just returns the same pre-recorded frame packet repeatedly."""

    @classmethod
    def fake_connect(cls, test_data_folder='test_data', frame_packet_filename='mocapframe_packet_v3.bin',
                     serverinfo_packet_filename='serverinfo_packet_v3.bin'):
        frame_packet = open(os.path.join(test_data_folder, frame_packet_filename), 'rb').read()
        server_info_packet = open(os.path.join(test_data_folder, serverinfo_packet_filename), 'rb').read()
        conn = FakeConnection([frame_packet], repeat=True)
        clock_synchronizer = FakeClockSynchronizer(deserialize(server_info_packet))
        return cls(conn, clock_synchronizer)
