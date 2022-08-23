"""Python Server Library for NOODLES Protocol

This server library implements the NOODLES messaging protocol and provides objects for 
maintaining a scene in state. The server uses a websocket connection to send CBOR encoded 
messages. To customize its implementation, the library provides convenient interface 
methods to assist the user in writing their own methods for the server. The user can also 
add custom delegates to add additionaly functionality to any of the standard components.

Modules:
    core.py
    geometry/
        geometry_creation.py
        geometry_objects.py
    interface.py
    noodle_objects.py
    server.py
"""


__version__ = "0.1.1"

from .server import start_server
from .interface import ServerTableDelegate, Delegate
from .core import Server
from . import geometry
from .noodle_objects import *

