# coding: utf-8

from attr import attrib, attrs

from .common import Version


@attrs(slots=True)
class ConnectMessage(object):

    payload = attrib(default='')  # type: str

    # Not sure why there are two of these, but the SDK sets them both to (3, 0, 0, 0).  Could be min
    # and max protocol version supported?
    version1 = attrib(default=Version(3))  # type: Version
    version2 = attrib(default=Version(3))  # type: Version

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
