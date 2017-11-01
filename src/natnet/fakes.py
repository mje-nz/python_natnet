# coding: utf-8

__all__ = ['FakeClient']

import time
import timeit

import attr

from .comms import Client
from .protocol import deserialize


@attr.s
class FakeConnection(object):
    """Fake connection class that returns the same pre-recorded frame packet repeatedly.

    Inject this into a Client to test receiving mocap frames without Motive running. """

    _frame_packet = attr.ib()  # type: bytes

    def wait_for_packet(self, timeout=None):
        if timeout:
            time.sleep(timeout)
        return self._frame_packet, timeit.default_timer()

    def wait_for_packet_with_id(self, id_):
        return self.wait_for_packet()

    def send_packet(self, packet):
        raise NotImplementedError()


@attr.s
class FakeClient(Client):

    """Fake NatNet client that just returns the same pre-recorded frame packet repeatedly."""

    @classmethod
    def fake_connect(cls, frame_packet_filename='tests/mocapframe_packet_v3.bin',
                     serverinfo_packet_filename='tests/serverinfo_packet_v3.bin'):
        conn = FakeConnection(open(frame_packet_filename, 'rb').read())
        server_info = deserialize(open(serverinfo_packet_filename, 'rb').read())
        return cls(conn, server_info)
