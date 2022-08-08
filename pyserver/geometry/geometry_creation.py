"""Module for assisting with the creation of geometry objects"""
from typing import Tuple
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



def set_up_attributes(input: nooobs.GeometryPatchInput):
    """Constructs attribute info from input lists"""

    # Add attribute info based on the input lists
    attribute_info = [] 
    position = nooobs.AttributeInput(
        semantic = "POSITION",
        format = "VEC3",
        normalized = False,
    )
    attribute_info.append(position)

    if input.normals:
        normal = nooobs.AttributeInput(
            semantic = "NORMAL",
            format = "VEC3",
            normalized = False,
        )
        attribute_info.append(normal)

    if input.tangents:
        tangent = nooobs.AttributeInput(
            semantic = "TANGENT",
            format = "VEC3",
            normalized = False,
        )
        attribute_info.append(tangent)

    if input.textures:
        texture = nooobs.AttributeInput(
            semantic = "TEXTURE",
            format = "U16VEC2",
            normalized = True,
        )
        attribute_info.append(texture)

    if input.colors:
        color = nooobs.AttributeInput(
            semantic = "COLOR",
            format = "U8VEC4",
            normalized = True,
            )
        attribute_info.append(color)

    # Use input to get offsets
    offset = 0
    for attribute in attribute_info:
        attribute.offset = offset
        offset += SIZES[attribute.format]

    # Use final offset to get stride
    for attribute in attribute_info:
        attribute.stride = offset

    return attribute_info

            
def build_geometry_buffer(server: core.Server, name, input: nooobs.GeometryPatchInput, 
    index_format: str, attribute_info: list) -> Tuple[nooobs.Buffer, int]:

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
    data = [x for x in [input.vertices, input.normals, input.tangents, input.textures, input.colors] if x]
    buffer_bytes = bytearray(0)
    points = zip(*data)
    for point in points:
        for info, attr in zip(point, attribute_info):

            # print(f"Point: {point}, P_Data: {info}")
            attr_size = format_map[attr.format]
            new_bytes = np.array(info, dtype=attr_size).tobytes(order='C')
            buffer_bytes.extend(new_bytes)
            # print(f"new bytes: {new_bytes}")

    index_offset = len(buffer_bytes)
    index_bytes = np.array(input.indices, dtype=format_map[index_format]).tobytes(order='C')
    #print(f"Index Bytes: {index_bytes}")
    buffer_bytes.extend(index_bytes)

    size = len(buffer_bytes)
    if size > 1000:
        # TODO - uri bytes
        raise Exception("TOO BIG")
    else:
        buffer = server.create_component(
            nooobs.Buffer,
            name = name,
            size = size,
            inline_bytes = buffer_bytes
        )
        return buffer, index_offset


def build_geometry_patch(server: core.Server, name: str, input: nooobs.GeometryPatchInput):

    vert_count = len(input.vertices)
    index_count = len(input.indices)
    index_format = get_format(vert_count)            

    # Set up attributes with given lists
    attribute_info = set_up_attributes(input)

    # Build buffer with given lists
    buffer: nooobs.Buffer
    buffer, index_offset = build_geometry_buffer(server, name, input, index_format, attribute_info)

    # Make buffer component
    buffer_view: nooobs.BufferView = server.create_component(
        nooobs.BufferView,
        name = name,
        source_buffer = buffer.id,
        type = "GEOMETRY",
        offset = 0, # What is this? cant always assume 0
        length = buffer.size
    )

    # Create attribute objects from buffer view and attribute info
    attributes = []
    for attribute in attribute_info:
        attr_obj = nooobs.Attribute(view=buffer_view.id, **dict(attribute))
        attributes.append(attr_obj)

    # Make index to describe indices at end of buffer
    index = nooobs.Index(
        view = buffer_view.id,
        count = index_count,
        offset = index_offset,
        format = index_format
    )

    # Finally create patch 
    patch = nooobs.GeometryPatch(
        attributes = attributes, 
        vertex_count = vert_count, 
        indices = index, 
        type = input.index_type, 
        material = input.material
    )

    return patch


def build_instance_buffer(server, name, matrix):
    """Build MAT4 Buffer"""
    
    buffer_bytes = np.array(matrix, dtype=np.single).tobytes(order='C')
    print(f"Instance buffer bytes: {buffer_bytes}")

    buffer = server.create_component(
        nooobs.Buffer,
        name = name,
        size = len(buffer_bytes),
        inline_bytes = buffer_bytes
    )

    return buffer


def build_entity(server: core.Server, geometry: nooobs.Geometry, matrix: nooobs.Mat4):

    name = geometry.name if geometry.name else None

    buffer: nooobs.Buffer = build_instance_buffer(server, name, matrix)
    
    buffer_view = server.create_component(
        nooobs.BufferView,
        name = f"Instance View for {name}",
        source_buffer = buffer.id,
        type = "UNK",
        offset = 0,
        length = buffer.size
    )
    
    instance = nooobs.InstanceSource(view=buffer_view.id, stride=0, bb=None)
    rep = nooobs.RenderRepresentation(mesh=geometry.id, instances=instance)

    entity = server.create_component(nooobs.Entity, name=name, render_rep=rep)
    
    return entity