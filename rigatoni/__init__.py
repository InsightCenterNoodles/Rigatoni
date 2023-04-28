"""Python Server Library for NOODLES Protocol

This server library implements the NOODLES messaging protocol and provides objects for 
maintaining a scene in state. The server uses a websocket connection to send CBOR encoded 
messages. To customize its implementation, the library provides convenient interface 
methods to assist the user in writing their own methods for the server. The user can also 
add custom delegates to add additionally functionality to any of the standard components.

Modules:
    core.py
    geometry/
        geometry_creation.py
        geometry_objects.py
    delegates.py
    noodle_objects.py
    server.py
"""


__version__ = "0.1.11"

from .delegates import ServerTableDelegate, Delegate
from .core import Server
from .noodle_objects import *

# Ensure that dependencies are installed for optional module
try:
    import numpy
except ImportError:
    numpy = None

if numpy is not None:
    from . import geometry
