# coding: utf-8

import attr

from .common import MessageId, register_message


@register_message(MessageId.RequestModelDef)
@attr.s
class RequestModelDefinitionsMessage(object):

    @classmethod
    def deserialize(cls, data=None, version=None):
        return cls()

    def serialize(self):
        return b''
