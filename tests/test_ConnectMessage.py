"""Tests for parsing and creating Connect messages."""

from optitrack.protocol import serialize, deserialize, ConnectMessage, Version


def test_parse_connect_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a Connect message."""
    data = open('tests/connect_packet_v3.bin', 'rb').read()
    info = deserialize(data, Version(3), strict=True)  # type: ConnectMessage

    assert info.payload == 'NatNetLib'
    assert info.version1 == Version(3)
    assert info.version2 == Version(3)


def test_serialize_connect_message():
    """Test serializing a Connect message."""
    expected = open('tests/connect_packet_v3.bin', 'rb').read()
    actual = serialize(ConnectMessage('NatNetLib', Version(3), Version(3)))

    assert actual == expected

