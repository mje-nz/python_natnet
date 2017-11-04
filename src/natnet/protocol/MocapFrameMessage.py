# coding: utf-8

try:
    # Only need this for type annotations
    from typing import Optional  # noqa: F401
except ImportError:
    pass

import attr

from .common import (MessageId, Version, double_t, float_t, int16_t, quaternion_t, register_message,
                     uint16_t, uint32_t, uint64_t, vector3_t)


@attr.s
class Markerset(object):

    name = attr.ib()  # type: str
    markers = attr.ib()

    @classmethod
    def deserialize(cls, data, version):
        name = data.unpack_cstr()
        marker_count = data.unpack(uint32_t)
        markers = [data.unpack(vector3_t) for i in range(marker_count)]
        return Markerset(name, markers)

    def serialize(self):
        return self.name.encode('utf-8') + b'\0' + uint32_t.pack(len(self.markers)) + \
               b''.join(vector3_t.pack(*marker) for marker in self.markers)


@attr.s
class RigidBody(object):

    id_ = attr.ib()  # type: int
    position = attr.ib()
    orientation = attr.ib()
    mean_error = attr.ib()  # type: Optional[float]
    _params = attr.ib()  # type: Optional[int]

    @classmethod
    def deserialize(cls, data, version):
        id_ = data.unpack(uint32_t)
        position = data.unpack(vector3_t)
        orientation = data.unpack(quaternion_t)

        if version < Version(3):
            # TODO: Store these?
            marker_count = data.unpack(uint32_t)
            marker_positions = [data.unpack(vector3_t) for i in range(marker_count)]  # noqa: F841

            if version >= Version(2):
                marker_ids = [data.unpack(uint32_t) for i in range(marker_count)]  # noqa: F841
                marker_sizes = [data.unpack(float_t) for i in range(marker_count)]  # noqa: F841

            padding = data.unpack(uint32_t)  # noqa: F841

        mean_error = None
        if version >= Version(2):
            mean_error = data.unpack(float_t)

        params = None
        if version >= Version(2, 6) or version.major == 0:
            # TODO: Shouldn't this be a uint16_t?
            params = data.unpack(int16_t)

        return cls(id_, position, orientation, mean_error, params)

    @property
    def tracking_valid(self):
        assert self._params is not None
        return (self._params & 0x01) != 0


@attr.s
class Skeleton(object):

    id_ = attr.ib()  # type: int
    rigid_bodies = attr.ib()  # type: list[RigidBody]

    @classmethod
    def deserialize(cls, data, version):
        id_ = data.unpack(uint32_t)
        rigid_body_count = data.unpack(uint32_t)
        rigid_bodies = [RigidBody.deserialize(data, version) for i in range(rigid_body_count)]
        return cls(id_, rigid_bodies)


@attr.s
class LabelledMarker(object):

    model_id = attr.ib()  # type: int
    marker_id = attr.ib()  # type: int
    position = attr.ib()
    size = attr.ib()  # type: float
    _params = attr.ib()  # type: Optional[int]
    residual = attr.ib()  # type: Optional[float]

    @classmethod
    def deserialize(cls, data, version):
        # In the SDK direct depacketization samples these are lumped together as one int32_t, but
        # this is what it decodes to.
        marker_id = data.unpack(uint16_t)
        model_id = data.unpack(uint16_t)

        position = data.unpack(vector3_t)
        size = data.unpack(float_t)

        params = None
        if version >= Version(2, 6) or version.major == 0:
            # TODO: Shouldn't this be a uint16_t?
            params = data.unpack(int16_t)

        residual = None
        if version >= Version(3) or version.major == 0:
            residual = data.unpack(float_t)

        return cls(model_id, marker_id, position, size, params, residual)

    @property
    def occluded(self):
        assert self._params is not None
        return (self._params & 0x01) != 0

    @property
    def point_cloud_solved(self):
        assert self._params is not None
        return (self._params & 0x02) != 0

    @property
    def model_solved(self):
        assert self._params is not None
        return (self._params & 0x04) != 0


@attr.s
class AnalogChannelData(object):

    values = attr.ib()  # type: list[int]

    @classmethod
    def deserialize(cls, data, version):
        frame_count = data.unpack(uint32_t)
        values = [data.unpack(uint32_t) for i in range(frame_count)]
        return cls(values)


@attr.s
class Device(object):

    id_ = attr.ib()  # type: int
    channels = attr.ib()  # type: list[AnalogChannelData]

    @classmethod
    def deserialize(cls, data, version):
        id_ = data.unpack(uint32_t)
        channel_count = data.unpack(uint32_t)
        channels = [AnalogChannelData.deserialize(data, version) for i in range(channel_count)]
        return cls(id_, channels)


@attr.s
class TimingInfo(object):

    timecode = attr.ib()  # type: int
    timecode_subframe = attr.ib()  # type: int
    timestamp = attr.ib()  # type: float
    camera_mid_exposure_timestamp = attr.ib()  # type: Optional[int]
    camera_data_received_timestamp = attr.ib()  # type: Optional[int]
    transmit_timestamp = attr.ib()  # type: Optional[int]

    @classmethod
    def deserialize(cls, data, version):
        timecode = data.unpack(uint32_t)
        timecode_subframe = data.unpack(uint32_t)

        if version >= Version(2, 7):
            timestamp = data.unpack(double_t)
        else:
            timestamp = data.unpack(float_t)

        camera_mid_exposure_timestamp = None
        camera_data_received_timestamp = None
        transmit_timestamp = None
        if version >= Version(3) or version.major == 0:
            camera_mid_exposure_timestamp = data.unpack(uint64_t)
            camera_data_received_timestamp = data.unpack(uint64_t)
            transmit_timestamp = data.unpack(uint64_t)

        return cls(timecode, timecode_subframe, timestamp, camera_mid_exposure_timestamp,
                   camera_data_received_timestamp, transmit_timestamp)


@register_message(MessageId.FrameOfData)
@attr.s
class MocapFrameMessage(object):

    frame_number = attr.ib()  # type: int
    markersets = attr.ib()  # type: list[Markerset]
    unlabelled_markers = attr.ib()
    rigid_bodies = attr.ib()  # type: list[RigidBody]
    skeletons = attr.ib()  # type: list[Skeleton]
    labelled_markers = attr.ib()  # type: list[LabelledMarker]
    force_plates = attr.ib()  # type: list[Device]
    devices = attr.ib()  # type:  list[Device]
    timing_info = attr.ib()  # type: TimingInfo
    _params = attr.ib()  # type: int

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize a ServerInfo message.

        :type data: ParseBuffer
        :type version: Version"""

        frame_number = data.unpack(uint32_t)

        markerset_count = data.unpack(uint32_t)
        markersets = [Markerset.deserialize(data, version) for i in range(markerset_count)]

        unlabelled_markers_count = data.unpack(uint32_t)
        unlabelled_markers = [data.unpack(vector3_t) for i in range(unlabelled_markers_count)]

        rigid_body_count = data.unpack(uint32_t)
        rigid_bodies = [RigidBody.deserialize(data, version) for i in range(rigid_body_count)]

        skeletons = []
        if version > Version(2):
            # TODO: Original version check here contradicted comment
            skeleton_count = data.unpack(uint32_t)
            skeletons = [Skeleton.deserialize(data, version) for i in range(skeleton_count)]

        labelled_markers = []
        if version >= Version(2, 3):
            # TODO: Original version check here contradicted PacketClient
            labelled_marker_count = data.unpack(uint32_t)
            labelled_markers = [LabelledMarker.deserialize(data, version) for i in range(labelled_marker_count)]

        force_plates = []
        if version >= Version(2, 9):
            force_plate_count = data.unpack(uint32_t)
            # Force plates and devices have the same data
            force_plates = [Device.deserialize(data, version) for i in range(force_plate_count)]

        devices = []
        if version >= Version(2, 11):
            device_count = data.unpack(uint32_t)
            devices = [Device.deserialize(data, version) for i in range(device_count)]

        timing_info = TimingInfo.deserialize(data, version)

        # TODO: Shouldn't this be a uint16_t?
        params = data.unpack(int16_t)

        # No idea what this is, but this is how long packets are
        unknown = data.unpack(uint32_t)  # noqa: F841

        return cls(frame_number, markersets, unlabelled_markers, rigid_bodies, skeletons, labelled_markers,
                   force_plates, devices, timing_info, params)

    @property
    def is_recording(self):
        assert self._params is not None
        return (self._params & 0x01) != 0

    @property
    def tracked_models_changed(self):
        assert self._params is not None
        return (self._params & 0x02) != 0
