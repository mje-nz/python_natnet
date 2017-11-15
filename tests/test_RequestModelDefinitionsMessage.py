"""Tests for parsing and creating RequestModelDefitions messages."""

from natnet.protocol import RequestModelDefinitionsMessage, Version, deserialize, serialize


def test_parse_requestmodeldef_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a RequestModelDefinitions message."""
    data = open('tests/requestmodeldef_packet_v3.bin', 'rb').read()
    deserialize(data, Version(3), strict=True)

    # No payload


def test_serialize_requestmodeldef_message():
    """Test serializing a RequestModelDefinitions message."""
    expected = open('tests/requestmodeldef_packet_v3.bin', 'rb').read()
    actual = serialize(RequestModelDefinitionsMessage())

    assert actual == expected
