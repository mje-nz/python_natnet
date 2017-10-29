"""Tests for parsing ServerInfo messages."""

from optitrack.protocol import ServerInfoMessage, Version


def test_parse_serverinfo_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a ServerInfo message."""
    data = open('test/serverinfo_packet_v3.bin', 'rb').read()
    info = ServerInfoMessage.deserialize(data[4:], Version(3))  # type: ServerInfoMessage

    # These values are verified against SampleClient where easy

    assert info.app_name == u'Motive'
    assert info.app_version == Version(2, 1)
    assert info.natnet_version == Version(3)
    assert info.high_resolution_clock_frequency == 3312787
    assert info.connection_info.data_port == 1511
    assert info.connection_info.multicast == True
    assert info.connection_info.multicast_address == u'239.255.42.99'
