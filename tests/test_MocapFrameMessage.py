"""Tests for parsing MocapFrame messages."""

import pytest

from natnet.protocol import MocapFrameMessage, Version, deserialize  # noqa: F401


def test_parse_mocapframe_packet_v3():
    """Test parsing a NatNet 3.0 packet containing a MocapFrame."""
    data = open('tests/mocapframe_packet_v3.bin', 'rb').read()
    frame = deserialize(data, Version(3), strict=True)  # type: MocapFrameMessage

    # These values are verified against SampleClient where easy

    assert frame.frame_number == 162734
    assert len(frame.markersets) == 0

    assert len(frame.unlabelled_markers) == 5
    # Assume markers 1-3 are correct if 0 and 4 are
    assert frame.unlabelled_markers[0] == pytest.approx((0.1272162, 1.5050275, -0.8858284))
    assert frame.unlabelled_markers[4] == pytest.approx((0.3213989, 1.4146513, -0.7529538))

    assert len(frame.rigid_bodies) == 1
    body = frame.rigid_bodies[0]
    assert body.id_ == 2
    assert body.position == pytest.approx((0.1744466, 1.4471314, -0.7343040))
    assert body.orientation == pytest.approx((-0.05459423, 0.5099482, 0.04370357, -0.8573577))
    assert body.mean_error == pytest.approx(0.0005152203)

    assert len(frame.skeletons) == 0

    assert len(frame.labelled_markers) == 6
    marker0 = frame.labelled_markers[0]
    assert marker0.model_id == 2
    assert marker0.marker_id == 1
    assert marker0.position == pytest.approx((0.1272162, 1.5050275, -0.8858284))
    assert marker0.size == pytest.approx(0.02143982)
    assert marker0._params == 10
    assert marker0.residual == pytest.approx(0.0002074828)
    # Assume markers 1-4 are correct if 0 and 5 are
    marker5 = frame.labelled_markers[5]
    assert marker5.model_id == 0
    assert marker5.marker_id == 50007
    assert marker5.position == pytest.approx((0.1708117, 1.5076591, -0.8402346))
    assert marker5.size == pytest.approx(0.02015734)
    assert marker5._params == 18
    assert marker5.residual == pytest.approx(0.0005593782)

    assert len(frame.force_plates) == 0
    assert len(frame.devices) == 0

    assert frame.timing_info.timecode == 0
    assert frame.timing_info.timecode_subframe == 0
    assert frame.timing_info.timestamp == pytest.approx(1356.117)
    assert frame.timing_info.camera_mid_exposure_timestamp == 1416497730518
    assert frame.timing_info.camera_data_received_timestamp == 1416497745808
    assert frame.timing_info.transmit_timestamp == 1416497748722

    assert frame._params == 0
