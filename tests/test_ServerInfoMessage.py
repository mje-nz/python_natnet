"""Tests for parsing ServerInfo messages."""

from optitrack.protocol import deserialize, ServerInfoMessage, Version


def test_parse_serverinfo_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a ServerInfo message."""
    data = open('tests/serverinfo_packet_v3.bin', 'rb').read()
    info = deserialize(data, Version(3), strict=True)  # type: ServerInfoMessage

    # These values are verified against SampleClient where easy

    assert info.app_name == u'Motive'
    assert info.app_version == Version(2, 1)
    assert info.natnet_version == Version(3)
    assert info.high_resolution_clock_frequency == 3312787
    assert info.connection_info.data_port == 1511
    assert info.connection_info.multicast == True
    assert info.connection_info.multicast_address == u'239.255.42.99'
