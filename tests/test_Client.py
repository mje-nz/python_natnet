"""Tests for Client class."""

import mock
import pytest

import natnet
from natnet.comms import ClockSynchronizer, Connection


class FakeConnection(Connection):

    def __init__(self, packets=None, received_times=None):
        """Fake connection which "receives" packets from a list, then raises SystemExit when it runs out of packets.

        Args:
            packets (list): Packets (from first to last)
            received_times (list): Received times
        """
        super(FakeConnection, self).__init__(command_socket=None, data_socket=None, command_address=None)
        self.packets = packets or []
        self.received_times = received_times or []
        assert len(self.packets) == len(self.received_times)

    def add_packet(self, packet, received_time):
        self.packets.append(packet)
        self.received_times.append(received_time)

    def add_message(self, message, received_time):
        self.add_packet(natnet.protocol.serialize(message), received_time)

    def wait_for_packet_raw(self, timeout=None):
        if self.packets:
            return self.packets.pop(0), self.received_times.pop(0)
        else:
            raise SystemExit

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


@pytest.fixture(scope='module')
def test_packets():
    server_info_packet = open('test_data/serverinfo_packet_v3.bin', 'rb').read()
    mocapframe_packet = open('test_data/mocapframe_packet_v3.bin', 'rb').read()
    modeldef_packet = open('test_data/modeldef_packet_v3.bin', 'rb').read()
    return server_info_packet, mocapframe_packet, modeldef_packet


@pytest.fixture(scope='module')
def test_messages(test_packets):
    server_info_packet, mocapframe_packet, modeldef_packet = test_packets
    server_info_message = natnet.protocol.deserialize(server_info_packet)  # type: natnet.protocol.ServerInfoMessage
    mocapframe_message = natnet.protocol.deserialize(mocapframe_packet)  # type: natnet.protocol.MocapFrameMessage
    modeldef_message = natnet.protocol.deserialize(modeldef_packet)   # type: natnet.protocol.ModelDefinitionsMessage
    return server_info_message, mocapframe_message, modeldef_message


@pytest.fixture
def client_with_fakes(test_messages):
    """Create client with fake connection and clock synchronizer."""
    server_info_message, _, _ = test_messages
    conn = FakeConnection()
    clock_synchronizer = FakeClockSynchronizer(server_info_message)
    return natnet.Client(conn, clock_synchronizer)


def test_client_calls_callback_for_mocapframe(client_with_fakes, test_packets, test_messages):
    client = client_with_fakes
    _, mocapframe_packet, _ = test_packets
    _, mocapframe_message, _ = test_messages

    # Fake current time to be the time the server sent the message
    received_time = client._clock_synchronizer.server_ticks_to_seconds(
            mocapframe_message.timing_info.transmit_timestamp)
    with mock.patch('timeit.default_timer', lambda: received_time):
        # Set wait_for_message to return a FrameOfData the first time, then raise SystemExit the second time
        client._conn.add_packet(mocapframe_packet, received_time)

        # Run the Client main loop with an inspectable callback
        callback = mock.Mock()
        client.set_callback(callback)
        client.spin()

    # Check call arguments
    callback.assert_called_once()
    (rigid_bodies, labelled_markers, timing), _ = callback.call_args
    assert rigid_bodies == mocapframe_message.rigid_bodies
    assert labelled_markers == mocapframe_message.labelled_markers
    assert timing.timestamp == pytest.approx(427584.91)
    # SampleClient says 5.5ms
    assert timing.system_latency == pytest.approx(0.005495071)
    # From fake time
    assert timing.transit_latency == 0
    assert timing.processing_latency == 0
    assert timing.latency == pytest.approx(0.005495071)


def test_client_calls_synchronizer_for_echo_response(client_with_fakes):
    client = client_with_fakes
    echo_response_message = natnet.protocol.EchoResponseMessage(0, 0)

    # Set wait_for_message to return a FrameOfData the first time, then raise SystemExit the second time
    client._conn.add_message(echo_response_message, 0)

    # Run the Client main loop
    client._clock_synchronizer.handle_echo_response = mock.Mock()
    client.spin()

    # Check call arguments
    client._clock_synchronizer.handle_echo_response.assert_called_once()
    args, kwargs = client._clock_synchronizer.handle_echo_response.call_args
    assert args == (echo_response_message, 0)


def test_client_connect(test_packets):
    with mock.patch('natnet.comms.ClockSynchronizer'):
        with mock.patch('natnet.comms.Connection') as MockedConnectionCls:
            # Make Connection.open(*) return a fake connection
            server_info_packet, _, modeldef_packet = test_packets
            conn = FakeConnection([server_info_packet, modeldef_packet], [0, 0])
            mock_conn = mock.Mock(wraps=conn)  # Add assert_called etc
            MockedConnectionCls.open.return_value = mock_conn

            # Call Client.connect
            client = natnet.Client.connect('192.168.0.106')

    # Checks
    assert client._conn.send_message.call_args_list[0] == mock.call(natnet.protocol.ConnectMessage())
    assert len(conn.packets) == 0
    client._conn.bind_data_socket.assert_called_once()
