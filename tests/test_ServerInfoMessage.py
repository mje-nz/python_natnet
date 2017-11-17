"""Tests for parsing ServerInfo messages."""

from natnet.protocol import ServerInfoMessage, Version, deserialize  # noqa: F401


def test_parse_serverinfo_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a ServerInfo message."""
    packet = open('test_data/serverinfo_packet_v3.bin', 'rb').read()
    info = deserialize(packet, Version(3), strict=True)  # type: ServerInfoMessage

    # These values are verified against SampleClient where easy

    assert info.app_name == u'Motive'
    assert info.app_version == Version(2, 1)
    assert info.natnet_version == Version(3)
    assert info.high_resolution_clock_frequency == 3312787
    assert info.connection_info.data_port == 1511
    assert info.connection_info.multicast == True  # noqa: E712
    assert info.connection_info.multicast_address == u'239.255.42.99'


def test_deserialize_serverinfo(benchmark):
    """Benchmark parsing a NatNet 3.0 packet containing a ServerInfo message."""
    packet = open('test_data/serverinfo_packet_v3.bin', 'rb').read()
    benchmark(deserialize, packet, Version(3))
