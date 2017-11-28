# coding: utf-8
"""ModelDef message implementation.

Copyright (c) 2017, Matthew Edwards.  This file is subject to the 3-clause BSD
license, as found in the LICENSE file in the top-level directory of this
distribution and at https://github.com/mje-nz/python_natnet/blob/master/LICENSE.
No part of python_natnet, including this file, may be copied, modified,
propagated, or distributed except according to the terms contained in the
LICENSE file.

This message contains descriptions of all tracked models (rigid bodies, skeletons, markersets) and devices.

It is not sent automatically when tracked models changes. The next FrameOfData will have a flag set, then the client
sends a RequestModelDefinitions message to prompt the server to send this.
"""

__all__ = ['ModelDefinitionsMessage', 'MarkersetDescription', 'RigidBodyDescription', 'SkeletonDescription',
           'ForcePlateDescription', 'DeviceDescription']
try:
    # Only need this for type annotations
    from typing import Optional  # noqa: F401
except ImportError:
    pass

import enum

import attr

from .common import MessageId, Version, int32_t, register_message, uint32_t, vector3_t


@attr.s
class MarkersetDescription(object):

    """Description of a markerset.

    Attributes:
        name (str):
        marker_names: (list[str])
    """

    name = attr.ib()
    marker_names = attr.ib()

    @classmethod
    def deserialize(cls, data, version=None):
        name = data.unpack_cstr()
        marker_count = data.unpack(uint32_t)
        marker_names = [data.unpack_cstr() for i in range(marker_count)]
        return cls(name, marker_names)


@attr.s
class RigidBodyDescription(object):

    """Description of a rigid body.

    Attributes:
        name (str): Rigid body name if available
        id\_ (int): Streaming ID
        parent_id (int): For a rigid body which is part of a hierarchy (i.e., a skeleton), the ID of the parent rigid
            body
        offset_from_parent (tuple[float, float, float]): (x, y, z) offset relative to parent
        marker_positions (list[tuple[float, float, float]]): List of marker positions, if available
        required_active_labels (list[int]): List of expected active marker labels, if available
    """

    name = attr.ib()  # type: Optional[str]
    id_ = attr.ib()
    parent_id = attr.ib()
    offset_from_parent = attr.ib()
    marker_positions = attr.ib()  # type: Optional[list[float, float, float]]
    required_active_labels = attr.ib()

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

    """Description of a skeleton.

    Attributes:
        name (str):
        id\_ (int): Streaming ID
        rigid_bodies (list[:class:`RigidBodyDescription`]):
    """

    name = attr.ib()
    id_ = attr.ib()
    rigid_bodies = attr.ib()

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

    """Tracked model definitions.

    Attributes:
        models: Mixed list of :class:`MarkersetDescription`, :class:`RigidBodyDescription`,
            :class:`SkeletonDescription`, :class:`ForcePlateDescription`, and :class:`DeviceDescription`."""

    models = attr.ib()  # type: list

    @classmethod
    def deserialize(cls, data, version):
        models = []

        definition_count = data.unpack(uint32_t)
        for i in range(definition_count):
            model_type = data.unpack(uint32_t)
            if model_type == ModelType.MarkerSet:
                models.append(MarkersetDescription.deserialize(data, version))
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

    def serialize(self):
        return uint32_t.pack(len(self.models)) + b''.join(m.serialize() for m in self.models)
