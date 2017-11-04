# coding: utf-8

import collections
import enum
import struct

import attr


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
    UnrecognizedRequest = 0x100  # NatNetTypes gives this as decimal 100, but that's incorrect


# Field types
bool_t = struct.Struct('?')
int16_t = struct.Struct('<h')
uint16_t = struct.Struct('<H')
uint32_t = struct.Struct('<I')
uint64_t = struct.Struct('<Q')
float_t = struct.Struct('<f')
double_t = struct.Struct('<d')
vector3_t = struct.Struct('<fff')
quaternion_t = struct.Struct('<ffff')


class ParseBuffer(object):

    def __init__(self, data):
        self.data = memoryview(data)
        self.offset = 0

    def __len__(self):
        """Length of remaining part of buffer."""
        return len(self.data) - self.offset

    def unpack(self, struct_type):
        value = struct_type.unpack(self.data[self.offset:self.offset + struct_type.size])
        if len(value) == 1:
            value = value[0]
        self.offset += struct_type.size
        return value

    def unpack_cstr(self, size=None):
        """Unpack a null-terminated string field.

        If size is given then always unpack that many bytes, otherwise unpack up to the first null.
        """
        field = self.data[self.offset:]
        if size:
            field = self.data[self.offset:self.offset + size]

        # TODO: Would this be better?
        # value = data.split('\0', 1)[0]
        value, _, _ = field.tobytes().partition(b'\0')

        if size:
            self.offset += size
        else:
            self.offset += len(value) + 1
        return value.decode('utf-8')

    def unpack_bytes(self, size):
        """Unpack a fixed-length field of bytes."""
        value = self.data[self.offset:self.offset + size].tobytes()
        self.offset += size
        return value


class Version(collections.namedtuple('Version', ('major', 'minor', 'build', 'revision'))):

    """NatNet version, with correct comparison operator.

    Believe it or not, this is performance-critical."""

    _version_t = struct.Struct('BBBB')

    def __new__(cls, major, minor=0, build=0, revision=0):
        return super(Version, cls).__new__(cls, major, minor, build, revision)

    @classmethod
    def deserialize(cls, data, version=None):
        return cls(*data.unpack(cls._version_t))

    def serialize(self):
        return self._version_t.pack(*self)


@attr.s
class SerDesRegistry(object):

    """Registry of message implementations which can serialize messages and deserialize packets."""

    _implementation_types = attr.ib(default=attr.Factory(dict))
    _version = attr.ib(default=Version(3))

    def register_message(self, id_):
        """Decorator to register the class which implements a given message."""

        def register_message_impl(cls):
            cls.message_id = id_
            self._implementation_types[id_] = cls
            return cls

        return register_message_impl

    @staticmethod
    def serialize(message):
        message_id = message.message_id
        payload = message.serialize()
        return uint16_t.pack(message_id) + uint16_t.pack(len(payload)) + payload

    @staticmethod
    def deserialize_header(data):
        """Deserialize a packet into header and payload.

        :type data: bytes"""
        data = ParseBuffer(data)
        message_id = MessageId(data.unpack(uint16_t))
        length = data.unpack(uint16_t)
        assert len(data) == length
        return message_id, data

    def deserialize_payload(self, message_id, payload_data, version=None, strict=False):
        """Deserialize the payload of a packet.

        :type message_id: MessageId
        :type payload_data: ParseBuffer
        :type version: Version
        :param strict: Raise an exception if there is data left in the buffer after parsing.
        :type strict: bool"""
        if version is None:
            version = self._version
        message_type = self._implementation_types[message_id]
        message = message_type.deserialize(payload_data, version)
        if strict:
            name = message_id.name
            assert len(payload_data) == 0, \
                "{} bytes remaining after parsing {} message".format(len(payload_data), name)
        return message

    def deserialize(self, data, version=None, strict=False):
        """Deserialize a packet into the message it contains.

        :type data: bytes
        :type version: Version
        :param strict: Raise an exception if there is data left in the buffer after parsing.
        :type strict: bool"""
        if version is None:
            version = self._version
        message_id, payload_data = self.deserialize_header(data)
        return self.deserialize_payload(message_id, payload_data, version, strict)


_registry = SerDesRegistry()
register_message = _registry.register_message
serialize = _registry.serialize
deserialize_header = _registry.deserialize_header
deserialize_payload = _registry.deserialize_payload
deserialize = _registry.deserialize
