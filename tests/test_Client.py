"""Tests for Client class."""

import timeit

import pytest

import natnet
from natnet.comms import Connection
from natnet.protocol import MessageId

try:
    from unittest import mock
except ImportError:
    import mock


@pytest.fixture(scope='module')
def test_packets():
    server_info = open('tests/serverinfo_packet_v3.bin', 'rb').read()
    mocapframe = open('tests/mocapframe_packet_v3.bin', 'rb').read()
    return {MessageId.ServerInfo: server_info, MessageId.FrameOfData: mocapframe}


def test_client_calls_callback(test_packets):
    # Create client with fake connection
    conn = mock.Mock(Connection)
    server_info = natnet.protocol.deserialize(test_packets[MessageId.ServerInfo])
    client = natnet.Client(conn, server_info)

    # Set wait_for_packet to return a FrameOfData the first time, then raise SystemExit the second time
    frame_packet = test_packets[MessageId.FrameOfData]
    received_time = timeit.default_timer()
    conn.wait_for_packet.side_effect = [(frame_packet, received_time), SystemExit]

    # Run the Client main loop with an inspectable callback
    callback = mock.Mock()
    client.set_callback(callback)
    client.spin()

    # Check call arguments
    callback.assert_called_once()
    (rigid_bodies, labelled_markers, timing), _ = callback.call_args
    frame = natnet.protocol.deserialize(frame_packet)  # type: natnet.protocol.MocapFrameMessage
    assert rigid_bodies == frame.rigid_bodies
    assert labelled_markers == frame.labelled_markers
    # SampleClient says 5.5ms
    assert timing.system_latency == pytest.approx(0.005495071)
    # Not sure if its worth testing the other members of timing
