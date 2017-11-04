# coding: utf-8

import attr

from .common import MessageId, Version, register_message


@register_message(MessageId.Connect)
@attr.s
class ConnectMessage(object):

    payload = attr.ib(default='')  # type: str

    # Not sure why there are two of these, but the SDK sets them both to (3, 0, 0, 0).  Could be min
    # and max protocol version supported?
    version1 = attr.ib(default=Version(3))  # type: Version
    version2 = attr.ib(default=Version(3))  # type: Version

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize a Connect message.

        :type data: ParseBuffer
        :type version: Version"""

        # TODO: Check SDK implementation

        payload = data.unpack_cstr(256)
        version1 = Version.deserialize(data, version)
        version2 = Version.deserialize(data, version)
        return cls(payload, version1, version2)

    def serialize(self):
        return self.payload.encode('utf-8') + b'\0'*(256 - len(self.payload)) \
               + self.version1.serialize() + self.version2.serialize()
