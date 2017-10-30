# coding: utf-8
"""NatNet protocol parsing."""

from .common import *
from .ConnectMessage import ConnectMessage
from .MocapFrameMessage import MocapFrameMessage
from .ServerInfoMessage import ServerInfoMessage

message_mapping = [
    (MessageId.Connect, ConnectMessage),
    (MessageId.ServerInfo, ServerInfoMessage),
    (MessageId.FrameOfData, MocapFrameMessage)
]


def serialize(message):
    message_id = [id_ for id_, type_ in message_mapping if type_ == type(message)][0]
    payload = message.serialize()
    return uint16_t.pack(message_id) + uint16_t.pack(len(payload)) + payload


def deserialize(data, version=Version(3), strict=False):
    data = ParseBuffer(data)
    message_id_ = data.unpack(uint16_t)
    length = data.unpack(uint16_t)
    assert len(data) == length
    message_type = [type_ for id_, type_ in message_mapping if id_ == message_id_][0]
    message = message_type.deserialize(data, version)
    if strict:
        name = MessageId(message_id_).name
        assert len(data) == 0, "{} bytes remaining after parsing {} message".format(len(data), name)
    return message
