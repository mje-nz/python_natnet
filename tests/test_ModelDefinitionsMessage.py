"""Tests for parsing ModelDefinitions messages."""

import pytest

from natnet.protocol import ModelDefinitionsMessage, Version, deserialize  # noqa: F401
from natnet.protocol.ModelDefinitionsMessage import MarkerSetDescription, RigidBodyDescription


def test_parse_modeldef_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a ModelDefinitions message."""
    packet = open('test_data/modeldef_packet_v3.bin', 'rb').read()
    modeldef = deserialize(packet, Version(3), strict=True)  # type: ModelDefinitionsMessage

    # These values are verified against SampleClient where easy

    assert len(modeldef.models) == 3

    # RaceQuad rigid body description
    rb = modeldef.models[0]  # type:  RigidBodyDescription
    assert type(rb) == RigidBodyDescription
    assert rb.name == 'RaceQuad'
    assert rb.id_ == 2
    assert rb.parent_id == -1
    assert rb.offset_from_parent == (0.0, 0.0, 0.0)
    assert rb.marker_positions[0] == pytest.approx((0.16115899, 0.0350516, -0.0321813))
    assert rb.marker_positions[1] == pytest.approx((-0.030819, 0.0397819, -0.0219901))
    assert rb.marker_positions[2] == pytest.approx((0.18753099, -0.0333833, 0.148081))
    assert rb.marker_positions[3] == pytest.approx((-0.0748715, 6.68607e-05, 0.0329233))
    assert rb.marker_positions[4] == pytest.approx((-0.0580382, -0.0319419, -0.136807))

    # RaceQuad markerset definition
    ms1 = modeldef.models[1]  # type: MarkerSetDescription
    assert type(ms1) == MarkerSetDescription
    assert ms1.name == 'RaceQuad'
    assert ms1.marker_names == ['Marker1', 'Marker2', 'Marker3', 'Marker4', 'Marker5']

    # 'all' markerset definition
    ms2 = modeldef.models[2]  # type: MarkerSetDescription
    assert type(ms2) == MarkerSetDescription
    assert ms2.name == 'all'
    assert ms2.marker_names == ['RaceQuad_1', 'RaceQuad_2', 'RaceQuad_3', 'RaceQuad_4',
                                'RaceQuad_5']
