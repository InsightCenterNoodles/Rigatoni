"""Geometry Creation Libary for Noodles Protocol

This library provides assistance with the creation of complex linked geometry components.
Users can use these built in methods as opposed to constructing buffers, buffer views,
entities, and geometries manually.
"""

from .geometry_creation import build_geometry_patch, build_entity, create_instances, update_entity, add_instances
from .geometry_objects import AttributeInput, GeometryPatchInput