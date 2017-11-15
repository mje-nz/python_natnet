# coding: utf-8

from .common import MessageId, register_message


@register_message(MessageId.RequestModelDef)
class RequestModelDefinitionsMessage(object):

    @classmethod
    def deserialize(cls, data=None, version=None):
        return cls()

    def serialize(self):
        return b''
