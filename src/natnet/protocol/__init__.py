# coding: utf-8
"""NatNet protocol parsing."""

__all__ = ['ConnectMessage', 'MocapFrameMessage', 'ServerInfoMessage', 'serialize', 'deserialize',
           'deserialize_header', 'deserialize_payload']

from .common import MessageId, ParseBuffer, Version, uint16_t
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


def deserialize_header(data):
    """Deserialize a packet into header and payload.

    :type data: bytes"""
    data = ParseBuffer(data)
    message_id = MessageId(data.unpack(uint16_t))
    length = data.unpack(uint16_t)
    assert len(data) == length
    return message_id, data


def deserialize_payload(message_id, payload_data, version=Version(3), strict=False):
    """Deserialize the payload of a packet.

    :type message_id: MessageId
    :type payload_data: ParseBuffer
    :type version: Version
    :param strict: Raise an exception if there is data left in the buffer after parsing.
    :type strict: bool"""
    message_type = [type_ for id_, type_ in message_mapping if id_ == message_id.value][0]
    message = message_type.deserialize(payload_data, version)
    if strict:
        name = message_id.name
        assert len(payload_data) == 0, \
            "{} bytes remaining after parsing {} message".format(len(payload_data), name)
    return message


def deserialize(data, version=Version(3), strict=False):
    """Deserialize a packet into the message it contains.

    :type data: bytes
    :type version: Version
    :param strict: Raise an exception if there is data left in the buffer after parsing.
    :type strict: bool"""
    message_id, payload_data = deserialize_header(data)
    return deserialize_payload(message_id, payload_data, version, strict)
