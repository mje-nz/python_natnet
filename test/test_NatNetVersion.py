"""Tests for NatNetVersion class."""
from optitrack.protocol import Version


def test_construct_default():
    """Test constructing with defaults."""
    version = Version(3)
    assert version.major == 3
    assert version.minor == 0
    assert version.build == 0
    assert version.revision == 0


def test_construct():
    """Test constructing with arguments."""
    version = Version(1, 2, 3, 4)
    assert version.major == 1
    assert version.minor == 2
    assert version.build == 3
    assert version.revision == 4


def test_comparisons_from_protocol_3_0():
    """Test that each comparison used in the parsers works for version 3.0."""
    version = Version(3)
    assert version > Version(2)
    assert version >= Version(2)
    assert version >= Version(2, 3)
    assert version >= Version(2, 6)
    assert version >= Version(2, 9)
    assert version >= Version(2, 11)
    assert version >= Version(3)
    assert not version < Version(3)
