# coding: utf-8
"""NatNet protocol parsing.

Each message is implemented as a class with a serialize method and/or deserialize classmethod
(messages are not required to implement both).

To deserialize a packet, use :func:`~natnet.protocol.deserialize` and check the type of the return
value (against the message types you're interested in).  Alternatively, use
:func:`~natnet.protocol.deserialize_header` and check the message ID (against the message IDs you're
interested in), then use :func:`~natnet.protocol.deserialize_payload` to get a message instance."""

__all__ = [
    # Functions
    'serialize', 'deserialize', 'deserialize_header', 'deserialize_payload',
    # Misc
    'MessageId', 'Version',
    # Messages
    'ConnectMessage', 'DiscoveryMessage', 'EchoRequestMessage', 'EchoResponseMessage',
    'MocapFrameMessage', 'ModelDefinitionsMessage', 'RequestModelDefinitionsMessage', 'ServerInfoMessage']

from .common import (MessageId, Version, deserialize, deserialize_header, deserialize_payload,
                     serialize)
from .ConnectMessage import ConnectMessage
from .DiscoveryMessage import DiscoveryMessage
from .EchoRequestMessage import EchoRequestMessage
from .EchoResponseMessage import EchoResponseMessage
from .MocapFrameMessage import MocapFrameMessage
from .ModelDefinitionsMessage import ModelDefinitionsMessage
from .RequestModelDefinitionsMessage import RequestModelDefinitionsMessage
from .ServerInfoMessage import ServerInfoMessage
