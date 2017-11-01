# coding: utf-8
"""This is only here because I typed it out by mistake and don't feel like doing it again."""

import attr


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

    # TODO: Implement
