# coding: utf-8

try:
    # Only need this for type annotations
    from typing import Optional  # noqa: F401
except ImportError:
    pass

import enum

import attr

from .common import MessageId, Version, int32_t, register_message, uint32_t, vector3_t


@attr.s
class MarkerSetDescription(object):

    name = attr.ib()  # type: str
    marker_names = attr.ib()

    @classmethod
    def deserialize(cls, data, version=None):
        name = data.unpack_cstr()
        marker_count = data.unpack(uint32_t)
        marker_names = [data.unpack_cstr() for i in range(marker_count)]
        return cls(name, marker_names)


@attr.s
class RigidBodyDescription(object):

    name = attr.ib()  # type: Optional[str]
    id_ = attr.ib()  # type: int
    parent_id = attr.ib()  # type: int
    offset_from_parent = attr.ib()
    marker_positions = attr.ib()
    required_active_labels = attr.ib()  # type: list[int]

    @classmethod
    def deserialize(cls, data, version, skip_markers=None):
        name = None
        if version >= Version(2):
            name = data.unpack_cstr()

        id_ = data.unpack(uint32_t)
        parent_id = data.unpack(int32_t)
        offset_from_parent = data.unpack(vector3_t)

        marker_positions = []
        required_active_labels = []

        # Marker positions are included in version 3, but apparently not when this rigid body is
        # inside a skeleton? I don't have the equipment to test this.
        if skip_markers is None:
            skip_markers = version < Version(3)
        if not skip_markers:
            marker_count = data.unpack(uint32_t)
            marker_positions = [data.unpack(vector3_t) for i in range(marker_count)]
            required_active_labels = [data.unpack(uint32_t) for i in range(marker_count)]

        return cls(name, id_, parent_id, offset_from_parent, marker_positions, required_active_labels)


@attr.s
class SkeletonDescription(object):

    name = attr.ib()  # type: str
    id_ = attr.ib()  # type: int
    rigid_bodies = attr.ib()  # type: list[RigidBodyDescription]

    @classmethod
    def deserialize(cls, data, version=None):
        name = data.unpack_cstr()
        id_ = data.unpack(int32_t)
        rigid_body_count = data.unpack(int32_t)
        rigid_bodies = [RigidBodyDescription.deserialize(data, version, skip_markers=True)
                        for i in range(rigid_body_count)]
        return cls(name, id_, rigid_bodies)


@attr.s
class ForcePlateDescription(object):

    id_ = attr.ib()
    serial_number = attr.ib()
    width = attr.ib()
    length = attr.ib()
    origin = attr.ib()
    calibration_matrix = attr.ib()
    corners = attr.ib()
    plate_type = attr.ib()
    channel_data_type = attr.ib()
    channels = attr.ib()
    channel_names = attr.ib()

    @classmethod
    def deserialize(cls, data, version=None):
        raise NotImplementedError


@attr.s
class DeviceDescription(object):

    id_ = attr.ib()  # type: int
    name = attr.ib()  # type: str
    serial_number = attr.ib()  # type: str
    device_type_ = attr.ib()  # type: int
    channel_data_type = attr.ib()  # type: int
    channel_names = attr.ib()  # type: list[str]

    @classmethod
    def deserialize(cls, data, version=None):
        raise NotImplementedError


class ModelType(enum.IntEnum):

    MarkerSet = 0
    RigidBody = 1
    Skeleton = 2
    # I assume:
    ForcePlate = 3
    Device = 4


@register_message(MessageId.ModelDef)
@attr.s
class ModelDefinitionsMessage(object):

    models = attr.ib()  # type: list

    @classmethod
    def deserialize(cls, data, version):
        models = []

        definition_count = data.unpack(uint32_t)
        for i in range(definition_count):
            model_type = data.unpack(uint32_t)
            if model_type == ModelType.MarkerSet:
                models.append(MarkerSetDescription.deserialize(data, version))
            elif model_type == ModelType.RigidBody:
                models.append(RigidBodyDescription.deserialize(data, version))
            elif model_type == ModelType.Skeleton:
                models.append(SkeletonDescription.deserialize(data, version))
            elif model_type == ModelType.ForcePlate:
                models.append(ForcePlateDescription.deserialize(data, version))
            elif model_type == ModelType.Device:
                models.append(DeviceDescription.deserialize(data, version))
            else:
                raise ValueError('Unknown model definition type {}'.format(model_type))

        return cls(models)
