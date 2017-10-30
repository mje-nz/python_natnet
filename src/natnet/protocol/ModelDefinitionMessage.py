# coding: utf-8
"""This is only here because I typed it out by mistake and don't feel like doing it again."""

from attr import attrib, attrs

from .common import *


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
