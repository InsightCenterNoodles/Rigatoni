"""Python Server Library for NOODLES Protocol

This server library implements the NOODLES messaging protocol and provides objects for 
maintaining a scene in state. The server uses a websocket connection to send CBOR encoded 
messages. To customize its implementation, the library provides convenient interface 
methods to assist the user in writing their own methods for the server. The user can also 
add custom delegates to add additionally functionality to any of the standard components.

Modules:
    core.py
    geometry/
        methods.py
        objects.py
    delegates.py
    noodle_objects.py
    server.py
"""


__version__ = "0.2.5"

from .core import Server
from .noodle_objects import *
from .byte_server import ByteServer

# Ensure that dependencies are installed for optional module
try:
    import numpy
    import meshio
    optionals = True
except ImportError:
    optionals = False

if optionals:
    from . import geometry
