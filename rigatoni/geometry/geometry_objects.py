"""Module with additional objects to help with geometry creation

These are based on the noodle_objects.py module and impliment validation
"""

from ..noodle_objects import *


class AttributeInput(NoodleObject):
    """Input for setting attributes of a buffer 
    
    User should not have to concern themselves with this input
    """

    semantic: AttributeSemantic
    format: Format
    normalized: bool
    offset: Optional[int]
    stride: Optional[int]


class GeometryPatchInput(NoodleObject):
    """User input object for creating a geometry patch"""

    vertices: list
    indices: list
    index_type: str 
    material: MaterialID
    normals: Optional[list] 
    tangents: Optional[list]
    textures:Optional[list] 
    colors: Optional[list]
