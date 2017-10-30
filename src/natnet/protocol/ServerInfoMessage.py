# coding: utf-8

import socket
from typing import Optional

from attr import attrib, attrs

from .common import *


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
        """Deserialize a ServerInfo message.

        :type data: ParseBuffer
        :type version: Version"""

        app_name = data.unpack_cstr(256)
        app_version = Version.deserialize(data, version)
        natnet_version = Version.deserialize(data, version)

        high_resolution_clock_frequency = None
        connection_info = None
        if version >= Version(3):
            high_resolution_clock_frequency = data.unpack(uint64_t)
            connection_info = ConnectionInfo.deserialize(data, version)

        return cls(app_name, app_version, natnet_version, high_resolution_clock_frequency, connection_info)
