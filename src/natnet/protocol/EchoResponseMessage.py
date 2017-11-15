# coding: utf-8

import attr

from .common import MessageId, ParseBuffer, Version, register_message, uint64_t  # noqa: F401


@register_message(MessageId.EchoResponse)
@attr.s
class EchoResponseMessage(object):

    request_timestamp = attr.ib()  # type: int
    received_timestamp = attr.ib()  # type: int

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize an EchoResponse message.

        :type data: ParseBuffer
        :type version: Version"""

        request_timestamp = data.unpack(uint64_t)
        received_timestamp = data.unpack(uint64_t)
        return cls(request_timestamp, received_timestamp)

    def serialize(self, version=None):
        return uint64_t.pack(self.request_timestamp) + uint64_t.pack(self.received_timestamp)
