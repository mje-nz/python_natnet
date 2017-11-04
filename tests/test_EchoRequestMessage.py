"""Tests for parsing and creating EchoRequest messages."""

from natnet.protocol import EchoRequestMessage, Version, deserialize, serialize  # noqa: F401


def test_parse_echorequest_packet_v3():
    """Test parsing a NatNet 3.0 packet containing an EchoRequest message."""
    data = open('tests/echorequest_packet_v3.bin', 'rb').read()
    echo_request = deserialize(data, Version(3), strict=True)  # type: EchoRequestMessage

    assert echo_request.timestamp == 278554190


def test_serialize_connect_message():
    """Test serializing an EchoRequest message."""
    expected = open('tests/echorequest_packet_v3.bin', 'rb').read()
    actual = serialize(EchoRequestMessage(278554190))

    assert actual == expected
