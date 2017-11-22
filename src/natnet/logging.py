# coding: utf-8
"""Logging implementation.

The purpose of this class is to allow console output to be replaced with ROS logger calls in
natnet_ros."""

from __future__ import print_function


class Logger(object):

    """Dummy logger implementation that just calls print."""

    @staticmethod
    def _log(msg, *args):
        """Print msg % args."""
        print(msg % args)

    debug = _log
    info = _log
    warning = _log
    error = _log
    fatal = _log
