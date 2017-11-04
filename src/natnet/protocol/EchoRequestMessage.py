# coding: utf-8

import attr

from .common import MessageId, ParseBuffer, Version, register_message, uint64_t  # noqa: F401


@register_message(MessageId.EchoRequest)
@attr.s
class EchoRequestMessage(object):

    timestamp = attr.ib()  # type: int

    @classmethod
    def deserialize(cls, data, version):
        """Deserialize an EchoRequest message.

        :type data: ParseBuffer
        :type version: Version"""

        send_timestamp = data.unpack(uint64_t)
        return cls(send_timestamp)

    def serialize(self, version=None):
        return uint64_t.pack(self.timestamp)
