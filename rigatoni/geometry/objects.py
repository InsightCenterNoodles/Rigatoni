"""Module with additional objects to help with geometry creation

These are based on the noodle_objects.py module and implement validation
"""

from typing import Optional

from .. import noodle_objects as nooobs


class AttributeInput(nooobs.NoodleObject):
    """Input for setting attributes of a buffer 
    
    User should not have to concern themselves with this input
    """

    semantic: nooobs.AttributeSemantic
    format: nooobs.Format
    normalized: bool
    offset: Optional[int] = None
    stride: Optional[int] = None


class GeometryPatchInput(nooobs.NoodleObject):
    """User input object for creating a geometry patch

    Attributes:
        vertices: List of vertices
        indices: Lists of indices corresponding to vertices
        index_type: Type of indices, one of "POINTS", "LINES", "LINE_LOOP",
            "LINE_STRIP", "TRIANGLES", and "TRIANGLE_STRIP"
        material: Material ID for the patch
        normals: List of normals corresponding to vertices
        tangents: List of tangents corresponding to vertices
        textures: List of texture coordinates corresponding to vertices
        colors: List of colors corresponding to vertices
    """

    vertices: list
    indices: list
    index_type: str 
    material: nooobs.MaterialID
    normals: Optional[list] 
    tangents: Optional[list]
    textures: Optional[list] 
    colors: Optional[list]


