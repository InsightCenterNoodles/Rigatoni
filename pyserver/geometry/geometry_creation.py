"""Module for assisting with the creation of geometry objects"""
import numpy as np

from .. import noodle_objects as nooobs
from .. import core 


SIZES = {
    # in bytes
    "U8": 1,
    "U16": 2,
    "U32": 4,
    "U8VEC4": 4,
    "U16VEC2": 4,
    "VEC2": 8,
    "VEC3": 12,
    "VEC4": 16,
    "MAT3": 36,
    "MAT4": 64
}


def get_format(num_vertices: int) -> str:
    """Helper to get format that can accomadate number of vertices"""

    if num_vertices < 256:
        return 'U8'
    elif num_vertices < 65536:
        return 'U16'
    else:
        return 'U32'


def get_attributes() -> list[nooobs.Attribute]:
    pass


def build_bytes():
    pass


def create_geometry(server: core.Server, name, vertices: list, attributes,
    indices: list, index_type, material: nooobs.IDGroup):
    """Help user create geometry as easily as possible"""

    # Geometry Info
    name = name
    patches = []

    # patch info
    attributes = attributes # Are attributes passed in as seperate lists? ex: colors
    vert_count = len(vertices)
        #index info
    index_offset = 'XXX' # Num bytes used for attributes
    stride = 0 # Is this always zero if indices are always tightly packed? - zero is default
    format = get_format(vert_count)
    index_count = len(indices)

    # Buffer Info
    bytes = build_bytes()
    size = len(bytes)
    # Choose uri or inline bytes?

    buffer = server.create_component(
        nooobs.Buffer,
        name = name,
        size = size
    )

    # Buffer View Info
    bf_offset = 0 # always the case? is in plottyn
    bf_length = index_offset + index.count * SIZES[index.format]

    buffer_view = server.create_component(
        nooobs.BufferView,
        name = name,
        source_buffer = buffer.id,
        type = "GEOMETRY",
        offset = bf_offset,
        length = bf_length
    )
    # Figure out stride, offset
    index = nooobs.Index(
        view = buffer_view, 
        count = index_count, 
        offset = index_offset, 
        stride = stride, 
        format = format
    )
    # Still need to figure out attributes
    patch = nooobs.GeometryPatch(
        attributes = attributes, 
        vertex_count = vert_count, 
        indices = index, 
        type = index_type, 
        material = material
    )
    patches.append(patch)

    server.create_component(nooobs.Geometry, name=name, patches=patches)



# Idea: use this object to keep track of all the objects while building
class GeometryCreator(object):
    """Object to facilitate creation of Geometry
    
    User should...
    1. Set up attributes
    2. Create a material
    3. Create geometry object
    """

    def __init__(self, server: core.Server, name: str=None):
        self.server = server
        self.name = name
        self.attributes: list[nooobs.Attribute] = []
        self.attribute_info: list[nooobs.AttributeInput] = []


    def set_up_attributes(self, set_up_info):
        """Pass in attribute info to set up attributes"""

        # set up with user input
        self.attribute_info = set_up_info 

        # Use input to get offsets
        offset = 0
        for attribute in self.attribute_info:
            attribute.offset = offset
            offset += SIZES[attribute.format]

        # Use final offset to get stride
        for attribute in self.attribute_info:
            attribute.stride = offset

              


    def build_buffer_bytes(self, data: list, indices: list, index_format: str):

        format_map = {
            "U8": np.int8,
            "U16": np.int16,
            "U32": np.int32,
            "U8VEC4": np.int8,
            "U16VEC2": np.int16,
            "VEC2": np.single,
            "VEC3": np.single,
            "VEC4": np.single,
            "MAT3": np.single,
            "MAT4": np.single
        }

        # Build the buffer
        buffer_bytes = bytearray(0)
        points = zip(*data)
        for point in points:
            for info, attr in zip(point, self.attribute_info):

                print(f"Point: {point}, P_Data: {info}")
                attr_size = format_map[attr.format]
                new_bytes = np.array(info, dtype=attr_size).tobytes(order='C')
                buffer_bytes.extend(new_bytes)
                print(f"new bytes: {new_bytes}")

        self.index_offset = len(buffer_bytes)
        index_bytes = np.array(indices, dtype=format_map[index_format]).tobytes(order='C')
        print(f"Index Bytes: {index_bytes}")
        buffer_bytes.extend(index_bytes)

        size = len(buffer_bytes)
        if size > 1000:
            # TODO
            raise Exception("TOO BIG")
        else:
            buffer = self.server.create_component(
                nooobs.Buffer,
                name = self.name,
                size = size,
                inline_bytes = buffer_bytes
            )
            return buffer


    def create_geometry_patch(self, vertices: list, 
        indices: list, index_type, material: nooobs.IDGroup,
        normals: list=None, tangents: list=None, colors: list=None,):
        # which of these should be optional? do they have to specify all?

        vert_count = len(vertices)
        index_count = len(indices)
        index_format = get_format(vert_count)

        # Filter out unspecified optional args and get buffer byte string
        data = [x for x in [vertices, normals, tangents, colors] if x]
        buffer: nooobs.Buffer = self.build_buffer_bytes(data, indices, index_format)

        # Make buffer component
        buffer_view: nooobs.BufferView = self.server.create_component(
            nooobs.BufferView,
            name = self.name,
            source_buffer = buffer.id,
            type = "GEOMETRY",
            offset = 0, # What is this? cant always assume 0
            length = buffer.size
        )

        # Update attributes
        for attribute in self.attribute_info:
            attr_obj = nooobs.Attribute(view=buffer_view.id, **dict(attribute))
            self.attributes.append(attr_obj)

        # Make index to describe indices at end of buffer
        index = nooobs.Index(
            view = buffer_view.id,
            count = index_count,
            offset = self.index_offset, # Temp value
            format = index_format
        )

        # Finally create patch 
        patch = nooobs.GeometryPatch(
            attributes = self.attributes, 
            vertex_count = vert_count, 
            indices = index, 
            type = index_type, 
            material = material
        )

        return patch