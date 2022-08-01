"""Module for assisting with the creation of geometry objects"""

from .. import noodle_objects as nooobs
from .. import core 

def create_geometry(server: core.Server, args):

    server.create_component(nooobs.Geometry, )