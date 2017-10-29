# coding: utf-8
"""NatNet protocol parsing."""

import collections
import enum
import socket
import struct
from typing import Optional

import attr
from attr import attrs, attrib


# Create structs for reading various object types to speed up parsing
bool_t = struct.Struct('?')
int16_t = struct.Struct('<h')
uint16_t = struct.Struct('<H')
uint32_t = struct.Struct('<I')
uint64_t = struct.Struct('<Q')
float_t = struct.Struct('<f')
double_t = struct.Struct('<d')
vector3_t = struct.Struct('<fff')
quaternion_t = struct.Struct('<ffff')


class MessageId(enum.IntEnum):

    """Message IDs as in NatNetTypes.h."""
    Connect = 0
    ServerInfo = 1
    Request = 2
    Response = 3
    RequestModelDef = 4
    ModelDef = 5
    RequestFrameOfData = 6
    FrameOfData = 7
    MessageString = 8
    Disconnect = 9
    KeepAlive = 10
    DisconnectByTimeout = 11
    EchoRequest = 12
    EchoResponse = 13
    Discovery = 14
    UnrecognizedRequest = 100


class ParseBuffer(object):

    def __init__(self, data):
        self.data = memoryview(data)
        self.offset = 0

    def unpack(self, struct_type):
        value = struct_type.unpack(self.data[self.offset:self.offset + struct_type.size])
        if len(value) == 1:
            value = value[0]
        self.offset += struct_type.size
        return value

    def unpack_cstr(self, size=None):
        """Unpack a null-terminated string.

        If size is given then always unpack that many bytes, otherwise unpack up to the first null.
        """
        field = self.data[self.offset:]
        if size:
            field = self.data[self.offset:self.offset + size]

        # TODO: Is this better?
        #value = data.split('\0', 1)[0]
        value, _, _ = bytes(self.data[self.offset:]).partition(b'\0')

        if size:
            self.offset += size
        else:
            self.offset += len(value) + 1
        return value.decode('utf-8')

    def unpack_bytes(self, size):
        value = bytes(self.data[self.offset:self.offset + size])
        self.offset += size
        return value


class Version(collections.namedtuple('Version', ('major', 'minor', 'build', 'revision'))):

    """NatNet version, with correct comparison operator.

    Believe it or not, this is performance-critical."""

    _version_t = struct.Struct('BBBB')

    def __new__(cls, major, minor=0, build=0, revision=0):
        return super(Version, cls).__new__(cls, major, minor, build, revision)

    @classmethod
    def deserialize(cls, data, version):
        return cls(*data.unpack(cls._version_t))


@attrs(slots=True)
class Markerset(object):

    name = attrib()  # type: str
    markers = attrib()

    @classmethod
    def deserialize(cls, data, version):
        name = data.unpack_cstr()
        marker_count = data.unpack(uint32_t)
        markers = [data.unpack(vector3_t) for i in range(marker_count)]
        return Markerset(name, markers)


@attrs(slots=True)
class RigidBody(object):

    id_ = attrib()  # type: int
    position = attrib()
    orientation = attrib()
    mean_error = attrib()  # type: Optional[float]
    params = attrib()  # type: Optional[int]

    @classmethod
    def deserialize(cls, data, version):
        id_ = data.unpack(uint32_t)
        position = data.unpack(vector3_t)
        orientation = data.unpack(quaternion_t)

        if version < Version(3):
            # TODO: Store these
            marker_count = data.unpack(uint32_t)
            marker_positions = [data.unpack(vector3_t) for i in range(marker_count)]

            if version >= Version(2):
                marker_ids = [data.unpack(uint32_t) for i in range(marker_count)]
                marker_sizes = [data.unpack(float_t) for i in range(marker_count)]

            padding = data.unpack(uint32_t)

        mean_error = None
        if version >= Version(2):
            mean_error = data.unpack(float_t)

        params = None
        if version >= Version(2, 6) or version.major == 0:
            # TODO: Shouldn't this be a uint16_t?
            params = data.unpack(int16_t)
            # TODO: Store this
            tracking_valid = (params & 0x01) != 0

        return cls(id_, position, orientation, mean_error, params)


@attrs(slots=True)
class Skeleton(object):

    id_ = attrib()  # type: int
    rigid_bodies = attrib()  # type: list[RigidBody]

    @classmethod
    def deserialize(cls, data, version):
        id_ = data.unpack(uint32_t)
        rigid_body_count = data.unpack(uint32_t)
        rigid_bodies = [RigidBody.deserialize(data, version) for i in range(rigid_body_count)]
        return cls(id_, rigid_bodies)


@attrs(slots=True)
class LabelledMarker(object):

    model_id = attrib()  # type: int
    marker_id = attrib()  # type: int
    position = attrib()
    size = attrib()  # type: float
    params = attrib()  # type: Optional[int]
    residual = attrib()  # type: Optional[float]

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
            # TODO: Store these
            occluded = (params & 0x01) != 0
            point_cloud_solved = (params & 0x02) != 0
            model_solved = (params & 0x04) != 0

        residual = None
        if version >= Version(3) or version.major == 0:
            residual = data.unpack(float_t)

        return cls(model_id, marker_id, position, size, params, residual)


@attrs(slots=True)
class AnalogChannelData(object):

    values = attrib()  # type: list[int]

    @classmethod
    def deserialize(cls, data, version):
        frame_count = data.unpack(uint32_t)
        values = [data.unpack(uint32_t) for i in range(frame_count)]
        return cls(values)


@attrs(slots=True)
class Device(object):

    id_ = attrib()  # type: int
    channels = attrib()  # type: list[AnalogChannelData]

    @classmethod
    def deserialize(cls, data, version):
        id_ = data.unpack(uint32_t)
        channel_count = data.unpack(uint32_t)
        channels = [AnalogChannelData.deserialize(data, version) for i in range(channel_count)]
        return cls(id_, channels)


@attrs(slots=True)
class TimingInfo(object):

    timecode = attrib()  # type: int
    timecode_subframe = attrib()  # type: int
    timestamp = attrib()  # type: float
    camera_mid_exposure_timestamp = attrib()  # type: Optional[int]
    camera_data_received_timestamp = attrib()  # type: Optional[int]
    transmit_timestamp = attrib()  # type: Optional[int]

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


@attrs(slots=True)
class MocapFrameMessage(object):

    frame_number = attrib()  # type: int
    markersets = attrib()  # type: list[Markerset]
    unlabelled_markers = attrib()
    rigid_bodies = attrib()  # type: list[RigidBody]
    skeletons = attrib()  # type: list[Skeleton]
    labelled_markers = attrib()  # type: list[LabelledMarker]
    force_plates = attrib()  # type: list[Device]
    devices = attrib()  # type:  list[Device]
    timing_info = attrib()  # type: TimingInfo
    params = attrib()  # type: int

    @classmethod
    def deserialize(cls, data, version):
        data = ParseBuffer(data)

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
        is_recording = (params & 0x01) != 0
        tracked_models_changed = (params & 0x02) != 0

        return cls(frame_number, markersets, unlabelled_markers, rigid_bodies, skeletons, labelled_markers,
                   force_plates, devices, timing_info, params)


@attrs(slots=True)
class ConnectionInfo(object):

    data_port = attrib()  # type: int
    multicast = attrib()  # type: bool
    _multicast_address = attrib()  # type: bytes

    @classmethod
    def deserialize(cls, data, version):
        data_port = data.unpack(uint16_t)
        multicast = data.unpack(bool_t)
        multicast_address = data.unpack_bytes(4)
        return cls(data_port, multicast, multicast_address)

    @property
    def multicast_address(self):
        """Return the multicast address as a string."""
        # TODO: Should use this instead of hardcoding multicast address
        return socket.inet_ntoa(self._multicast_address)


@attrs(slots=True)
class ServerInfoMessage(object):

    app_name = attrib()  # type: str
    app_version = attrib()  # type: Version
    natnet_version = attrib()  # type: Version
    high_resolution_clock_frequency = attrib()  # type: Optional[int]
    connection_info = attrib()  # type: Optional[ConnectionInfo]

    @classmethod
    def deserialize(cls, data, version):
        data = ParseBuffer(data)

        app_name = data.unpack_cstr(256)
        app_version = Version.deserialize(data, version)
        natnet_version = Version.deserialize(data, version)

        high_resolution_clock_frequency = None
        connection_info = None
        if version >= Version(3):
            high_resolution_clock_frequency = data.unpack(uint64_t)
            connection_info = ConnectionInfo.deserialize(data, version)

        return cls(app_name, app_version, natnet_version, high_resolution_clock_frequency, connection_info)


@attrs(slots=True)
class ForcePlateDescription(object):
    id_ = attrib()
    serial_number = attrib()
    width = attrib()
    length = attrib()
    origin = attrib()
    calibration_matrix = attrib()
    corners = attrib()
    plate_type = attrib()
    channel_data_type = attrib()
    channels = attrib()
    channel_names = attrib()

    # TODO: Implement


if __name__ == '__main__':
    import yaml
    # https://stackoverflow.com/a/8661021
    represent_dict_order = lambda self, data: self.represent_mapping('tag:yaml.org,2002:map',
                                                                     data.items())
    yaml.add_representer(collections.OrderedDict, represent_dict_order)

    data = open('../test/mocapframe_packet_v3.bin', 'rb').read()
    frame = MocapFrameMessage.deserialize(data[4:], Version(3))
    print(yaml.dump(attr.asdict(frame, dict_factory=collections.OrderedDict), default_flow_style=False))

    import timeit
    n = 10000
    t = timeit.timeit('MocapFrameMessage.deserialize(data[4:], Version(3))', globals=locals(), number=n)
    print('Parsing time: {} us'.format(t/n*1e6))
