# coding: utf-8

"""This is the most complicated message.

All positions are given as (x, y, z) tuples of floats, in meters, in whatever co-ordinate frame
Motive is using (Y-up or Z-up depending on the streaming settings).  All orientations are given in
quaternion form as (x, y, z, w) tuples of floats.

Note that I have only tested rigid bodies -- skeletons, force plates and peripheral devices may or
may not work.
"""

__all__ = ['Markerset', 'RigidBody', 'Skeleton', 'LabelledMarker', 'AnalogChannelData', 'Device',
           'TimingInfo', 'MocapFrameMessage']

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

    """Vaguely-defined grouping of markers which doesn't seem to serve any useful purpose.

    Attributes:
        name (str): Markerset name
        markers (list[tuple[float, float, float]]): Position for each marker
    """

    name = attr.ib()
    markers = attr.ib()

    @classmethod
    def deserialize(cls, data, version=None):
        """Deserialize a Markerset from a ParseBuffer."""
        name = data.unpack_cstr()
        marker_count = data.unpack(uint32_t)
        markers = [data.unpack(vector3_t) for i in range(marker_count)]
        return Markerset(name, markers)

    def serialize(self):
        return self.name.encode('utf-8') + b'\0' + uint32_t.pack(len(self.markers)) + \
               b''.join(vector3_t.pack(*marker) for marker in self.markers)


@attr.s
class RigidBody(object):

    """Rigid body data.

    Note that as of NatNet 3, the individual marker positions, IDs and sizes are not included here
    (and if you don't need them you can prevent Motive from streaming them at all).  If you need
    them, search the list of LabelledMarkers for markers with the right model ID.

    Attributes:
        id (int): Streaming ID
        position (tuple[float, float, float]):
        orientation (tuple([float, float, float, float]):
        mean_error (float or None): Mean error per marker, if available
    """

    id_ = attr.ib()  # type: int
    position = attr.ib()
    orientation = attr.ib()
    mean_error = attr.ib()  # type: Optional[float]
    _params = attr.ib()  # type: Optional[int]

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize a RigidBody from a ParseBuffer."""
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
        """True if rigid body is being tracked successfully."""
        assert self._params is not None
        return (self._params & 0x01) != 0


@attr.s
class Skeleton(object):

    """Skeleton data, which consists of a set of rigid bodies.

    Apparently the rigid bodies will have their ID equal to skeleton_id << 16 + bone_id.

    Attributes:
        id_ (int): Skeleton ID (I'm not sure where this is set)
        rigid_bodies (list[:class:`RigidBody`]):
    """

    id_ = attr.ib()  # type: int
    rigid_bodies = attr.ib()  # type: list[RigidBody]

    @classmethod
    def deserialize(cls, data, version=None):
        """Deserialize a Skeleton from a ParseBuffer."""
        id_ = data.unpack(uint32_t)
        rigid_body_count = data.unpack(uint32_t)
        rigid_bodies = [RigidBody.deserialize(data, version) for i in range(rigid_body_count)]
        return cls(id_, rigid_bodies)


@attr.s
class LabelledMarker(object):

    """A single marker and associated information.

    Note that this is **not** only markers that are part of rigid bodies.

    Attributes:
        model_id (int): ID of containing rigid body, or 0 if the marker is not part of a rigid body
        marker_id (int): Marker ID (starting at 0 for rigid body markers, or a large number
            otherwise)
        position (tuple[float, float, float]):
        size (float): Estimated marker size in meters
        residual (float or None): Marker error in mm/ray, if available
    """

    model_id = attr.ib()
    marker_id = attr.ib()
    position = attr.ib()
    size = attr.ib()
    _params = attr.ib()  # type: Optional[int]
    residual = attr.ib()

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize a LabelledMarker from a ParseBuffer."""
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
        """True if the marker is occluded."""
        assert self._params is not None
        return (self._params & 0x01) != 0

    @property
    def point_cloud_solved(self):
        """True if the marker is "point cloud solved" i.e. its position was calculated directly."""
        assert self._params is not None
        return (self._params & 0x02) != 0

    @property
    def model_solved(self):
        """True if the marker is "model solved" i.e. its position was calculated from a rigid body."""
        assert self._params is not None
        return (self._params & 0x04) != 0


@attr.s
class AnalogChannelData(object):

    values = attr.ib()  # type: list[int]

    @classmethod
    def deserialize(cls, data, version=None):
        frame_count = data.unpack(uint32_t)
        values = [data.unpack(uint32_t) for i in range(frame_count)]
        return cls(values)


@attr.s
class Device(object):

    id_ = attr.ib()  # type: int
    channels = attr.ib()  # type: list[AnalogChannelData]

    @classmethod
    def deserialize(cls, data, version=None):
        id_ = data.unpack(uint32_t)
        channel_count = data.unpack(uint32_t)
        channels = [AnalogChannelData.deserialize(data, version) for i in range(channel_count)]
        return cls(id_, channels)


@attr.s
class TimingInfo(object):

    """Timing information.

    Attributes:
        timecode (int): SMPTE timecode, if available
        timecode_subframe (int): SMPTE timecode subframe, if available
        timestamp (float): Software timestamp (in seconds since software startup)
        camera_mid_exposure_timestamp (int or None): Camera mid exposure time (in performance
            counter ticks), if available
        camera_data_received_timestamp (int or None): Time camera data was received (in performance
            counter ticks), if available
        transmit_timestamp (int or None): Time frame was transmitted (in performance counter ticks),
            if available
    """

    timecode = attr.ib()
    timecode_subframe = attr.ib()
    timestamp = attr.ib()
    camera_mid_exposure_timestamp = attr.ib()
    camera_data_received_timestamp = attr.ib()
    transmit_timestamp = attr.ib()

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize timing information from a ParseBuffer."""
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

    """Frame of mocap data.

    Attributes:
        frame_number (int):
        markersets (list of :class:`Markerset`):
        unlabelled_markers (list[tuple[float, float, float]]): Position of each tracked marker,
            whether part of a rigid body or not (deprecated)
        rigid_bodies (list of :class:`RigidBody`):
        skeletons (list of :class:`Skeleton`):
        labelled_markers (list of :class:`LabelledMarker`): A LabelledMarker instance for each
            tracked marker, whether part of a rigid body or not
        force_plates (list of :class:`Device`):
        devices (list of :class:`Device`):
        timing_info (:class:`TimingInfo`): Timestamps (in server time)
    """

    frame_number = attr.ib()
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
        """Deserialize a FrameOfData message.

        Args:
            data (:class:`~common.ParseBuffer`):
            version (:class:`~common.Version`):

        Returns:
            MocapFrameMessage: Deserialized message
        """

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
        """True if Motive is recording."""
        assert self._params is not None
        return (self._params & 0x01) != 0

    @property
    def tracked_models_changed(self):
        """True if the tracked models have changed since the last frame."""
        assert self._params is not None
        return (self._params & 0x02) != 0
