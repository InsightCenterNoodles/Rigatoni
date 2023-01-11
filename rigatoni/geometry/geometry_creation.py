"""Module for assisting with the creation of geometry objects"""
from math import sqrt
from collections import deque
from statistics import mean
from typing import Optional, Tuple
import numpy as np
import meshio

from .. import noodle_objects as nooobs
from ..core import Server

from .geometry_objects import AttributeInput, GeometryPatchInput
from .byte_server import ByteServer

INLINE_LIMIT = 10000

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

FORMAT_MAP = {
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

DEFAULT_POSITION = [0.0, 0.0, 0.0, 1.0]
DEFAULT_COLOR = [1.0, 1.0, 1.0, 1.0]
DEFAULT_ROTATION = [0.0, 0.0, 0.0, 1.0]
DEFAULT_SCALE = [1.0, 1.0, 1.0, 1.0]


def get_format(num_vertices: int) -> str:
    """Helper to get format that can accomadate number of vertices
    
    Args:
        num_vertices (int): number of vertices needed to store in mesh
    """

    if num_vertices < 256:
        return 'U8'
    elif num_vertices < 65536:
        return 'U16'
    else:
        return 'U32'


def set_up_attributes(input: GeometryPatchInput, generate_normals: bool):
    """Constructs attribute info from input type
    
    Takes list input and constructs objects 
    that can be used in build_geometry_patch

    Args:
        input (GeometryPatchInput): stores lists of vertices, indices
            index type, material, and possibly normals, tangents,
            textures, and colors
    """

    # Generate normals if not indicated in input
    if not input.normals and generate_normals:
        input.normals = calculate_normals(input.vertices, input.indices)

    # Add attribute info based on the input lists
    attribute_info = [] 
    position = AttributeInput(
        semantic = "POSITION",
        format = "VEC3",
        normalized = False,
    )
    attribute_info.append(position)

    normal = AttributeInput(
        semantic = "NORMAL",
        format = "VEC3",
        normalized = False,
    )
    attribute_info.append(normal)

    if input.tangents:
        tangent = AttributeInput(
            semantic = "TANGENT",
            format = "VEC3",
            normalized = False,
        )
        attribute_info.append(tangent)

    if input.textures:
        texture = AttributeInput(
            semantic = "TEXTURE",
            format = "U16VEC2",
            normalized = True,
        )
        attribute_info.append(texture)

    if input.colors:
        color = AttributeInput(
            semantic = "COLOR",
            format = "U8VEC4",
            normalized = True,
            )
        attribute_info.append(color)

        # Check color format and correct
        if any(i > 1 for i in input.colors[0]):
            for i in range(len(input.colors)):
                input.colors[i] = [x / 255 for x in input.colors[i]]

    # Use input to get offsets
    offset = 0
    for attribute in attribute_info:
        attribute.offset = offset
        offset += SIZES[attribute.format]

    # Use final offset to get stride
    for attribute in attribute_info:
        attribute.stride = offset

    return attribute_info

            
def build_geometry_buffer(server: Server, name, input: GeometryPatchInput, 
    index_format: str, attribute_info: list[AttributeInput], byte_server: ByteServer=None) -> Tuple[nooobs.Buffer, int]:
    """Builds a buffer component

    Args:
        server (Server): server to create component on
        name (str): name to give component
        input (GeometryPatchInput): lists of attributes and point data 
        index_format (str): format the indices should take
        attribute_info (list[AttributeInput]): Info on the attributes, mostly used for formatting
        byte_server (ByteServer): byte server to use if needed
    """

    # Filter out inputs unspecified by user, and group attributes by point
    data = [x for x in [input.vertices, input.normals, input.tangents, input.textures, input.colors] if x]
    points = zip(*data)

    # Build byte array by iteating through points and their attributes
    buffer_bytes = bytearray(0)
    for point in points:
        for info, attr in zip(point, attribute_info):
            attr_size = FORMAT_MAP[attr.format]
            new_bytes = np.array(info, dtype=attr_size).tobytes(order='C')
            buffer_bytes.extend(new_bytes)

    # Add index bytes to byte array
    index_offset = len(buffer_bytes)
    index_bytes = np.array(input.indices, dtype=FORMAT_MAP[index_format]).tobytes(order='C')
    buffer_bytes.extend(index_bytes)

    # Create buffer component using uri bytes if needed
    size = len(buffer_bytes)
    if size > INLINE_LIMIT:
        print(f"Large Mesh: Using URI Bytes")
        uri = byte_server.add_buffer(buffer_bytes)
        buffer = server.create_component(
            nooobs.Buffer,
            name = name,
            size = size,
            uri_bytes = uri
        )
        return buffer, index_offset
    else:
        buffer = server.create_component(
            nooobs.Buffer,
            name = name,
            size = size,
            inline_bytes = buffer_bytes
        )
        return buffer, index_offset


def build_geometry_patch(server: Server, name: str, input: GeometryPatchInput, 
    byte_server: ByteServer=None, generate_normals: bool=True) -> nooobs.GeometryPatch:
    """Build a Geometry Patch with related buffers and views
    
    Args:
        server (Server): server to create components on
        name (str): name for the components
        input (GeometryPatch): input lists with data to create the patch
        byte_server (ByteServer): optional server to use if mesh is larger than 10Kb
    """

    # Set up some constants
    vert_count = len(input.vertices)
    index_count = len(input.indices) * len(input.indices[0])
    index_format = get_format(vert_count)            

    # Set up attributes with given lists
    attribute_info = set_up_attributes(input, generate_normals=generate_normals)

    # Build buffer with given lists
    buffer: nooobs.Buffer
    buffer, index_offset = build_geometry_buffer(server, name, input, index_format, attribute_info, byte_server)

    # Make buffer view component
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


def build_instance_buffer(server: Server, name: str, matrices: nooobs.Mat4) -> nooobs.Buffer:
    """Build Buffer from Mat4 to Represent Instances
    
    Args:
        server (Server): server to put buffer component on
        name (str): name for the buffer
        matrices (Mat4): instance matrices
    """
    
    buffer_bytes = np.array(matrices, dtype=np.single).tobytes()

    buffer = server.create_component(
        nooobs.Buffer,
        name = f"Instance buffer for {name}",
        size = len(buffer_bytes),
        inline_bytes = buffer_bytes
    )

    return buffer


def build_entity(server: Server, geometry: nooobs.Geometry, instances: list[nooobs.Mat4]=None):
    """Build Entity from Geometry
    
    Args:
        server (Server): server to build entity component on
        geometry (Geometry): geometry to link entity to
        instances (Mat4): optional instance matrix, can use create_instances to generate
    """

    # Set name to match geometry
    name = geometry.name if geometry.name else None

    # Create instance buffer and view if specified
    if instances:
        buffer = build_instance_buffer(server, name, instances)
        buffer_view = server.create_component(
            nooobs.BufferView,
            name = f"Instance View for {name}",
            source_buffer = buffer.id,
            type = "UNK",
            offset = 0,
            length = buffer.size
        )
        instance = nooobs.InstanceSource(view=buffer_view.id, stride=0, bb=None)
    else:
        instance = None

    # Create render rep and entity from geometry and instances
    rep = nooobs.RenderRepresentation(mesh=geometry.id, instances=instance)
    entity = server.create_component(nooobs.Entity, name=name, render_rep=rep)
    
    return entity


def create_instances(
    positions: list[nooobs.Vec3] = [], 
    colors: list[nooobs.Vec4] = [], 
    rotations: list[nooobs.Vec4] = [], 
    scales: list[nooobs.Vec3] = []) -> list[nooobs.Mat4]:
    """Create new instances for an entity
    
    All lists are optional and will be filled with defaults
    By default one instance is created at least
    Lists are padded out to 4 values

    Args:
        positions (list[Vec3]): positions for each instance
        colors (list[Vec4]): Colors for each instance
        rotations (list[Vec4]): Rotations for each instance
        scales (list[Vec3]): Scales for each instance
    """

    def padded(lst: list, defuault_val: float=1.0):
        """Helper to pad the lists"""

        lst = list(lst)
        if len(lst) < 4:
            lst += [defuault_val] * (4 - len(lst))
        return lst

    # If no inputs specified create one default instance
    if not (positions or colors or rotations or scales):
        positions = [DEFAULT_POSITION]

    # Use longest input as number of instances
    num_instances = max([len(l) for l in [positions, colors, rotations, scales]])

    # Build the matrices and extend
    instances = []
    for i in range(num_instances):
        position = padded(positions[i]) if i < len(positions) else DEFAULT_POSITION
        color = padded(colors[i]) if i < len(colors) else DEFAULT_COLOR
        rotation = padded(rotations[i]) if i < len(rotations) else DEFAULT_ROTATION
        scale = padded(scales[i]) if i < len(scales) else DEFAULT_SCALE
        instances.extend([position, color, rotation, scale])

    return instances


def update_entity(server: Server, entity: nooobs.Entity, geometry: nooobs.Geometry=None, instances: list=None):
    """Update an entity with new instances or geometry
    
    Args:
        server (Server): server with entity to update
        entity (Entity): Entity to be updated
        geometry (Geometry): Optional new geometry if that is being changed
        instances (list[Mat4]): Optional new instances if that is changed
    """

    # Get name from entity if applicable
    name = entity.name if entity.name else None

    # Get render rep and ensure entity is working with geometry
    old_rep = entity.render_rep
    if not old_rep:
        raise Exception("Entity isn't renderable")

    # Set geometry id based on whether there is new geometry or not
    if geometry:
        mesh = geometry.id
    else:
        mesh = old_rep.mesh

    # Build new buffer / view for instances or use existing instances
    if instances:
        buffer = build_instance_buffer(server, name, instances)
        buffer_view = server.create_component(
            nooobs.BufferView,
            name = f"Instance View for {name}",
            source_buffer = buffer.id,
            type = "UNK",
            offset = 0,
            length = buffer.size
        )
        instance = nooobs.InstanceSource(view=buffer_view.id, stride=0, bb=None)
    else:
        instance = old_rep.instances

    # Create new render rep for entity and update entity
    rep = nooobs.RenderRepresentation(mesh=mesh, instances=instance)
    entity.render_rep = rep
    entity = server.update_component(entity)

    # Clean up old components with deletes
    if instances:
        server.delete_component(server.components[old_rep.instances.view].source_buffer)
        server.delete_component(old_rep.instances.view)
    elif geometry:
        server.delete_component(old_rep.mesh)
    
    return entity


def add_instances(server: Server, entity: nooobs.Entity, instances: list):
    """Add instances to an existing entity
    
    Args:
        server (Server): server with entity to update
        entity (Entity): entity to be updated
        instances (list[Mat4]): new instances to be added, can be generated using 
            create_instances()
    """

    # Ensure we're working with an renderable entity
    try:
        rep = entity.render_rep
    except:
        raise Exception("Entity isn't renderable")

    # Get old instance buffer from entity's render rep
    old_view: nooobs.BufferView = server.components[rep.instances.view]
    old_buffer: nooobs.Buffer = server.components[old_view.source_buffer]
    old_instances = np.frombuffer(old_buffer.inline_bytes, dtype=np.single)

    # Combine new and old instances
    combined = np.append(old_instances, instances)

    update_entity(server, entity, instances=combined.tolist())



#---------------------------------- Mesh Importing ----------------------------------#

def convert(color: int):
    """Helper to convert decimal pymesh values to RGBA array"""

    rgb = []
    for i in range(4):
        rgb.append(color % 256)
        color = color // 256

    alpha = rgb.pop(0)
    rgb.append(alpha)
    return rgb


def meshlab_load(server: Server, byte_server: ByteServer, file, 
    material: nooobs.Material, mesh_name: Optional[str]=None, generate_normals: bool=True):
    """Use pymeshlab to load types unsupported by meshio

    This method is only called from geometry_from_mesh if needed
    
    Args:   
        server (Server): server to load geometry onto
        byte_server (ByteServer): server to support URI bytes if needed
        file (str, path): file to load mesh from
        material (Material): material to use in geometry
        mesh_name (str): optional name
    """
    import pymeshlab
    
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(file)
    mesh = ms.current_mesh()
    #mesh.compute_normal_per_vertex("Simple Average")
    print(f"Finished Loading Mesh...")

    # Extract data from mesh set structure
    vertices = mesh.vertex_matrix().tolist()
    indices = mesh.face_matrix().tolist()
    #normals = mesh.vertex_normal_matrix().tolist() # Look like they could be off
    normals = None
    tangents = None # TBD
    textures = None # TBD
    colors = [convert(color) for color in mesh.vertex_color_array().tolist()]

    # Create patch / geometry for point geometry
    patches = []
    patch_info = GeometryPatchInput(
        vertices = vertices, 
        indices = indices, 
        index_type = "TRIANGLES",
        material = material.id,
        normals = normals,
        tangents = tangents,
        textures = textures,
        colors = colors)
    patches.append(build_geometry_patch(server, mesh_name, patch_info, byte_server, generate_normals=generate_normals))
    geometry = server.create_component(nooobs.Geometry, name=mesh_name, patches=patches)

    return geometry


def geometry_from_mesh(server: Server, file, material: nooobs.Material, 
    mesh_name: Optional[str]=None, byte_server: ByteServer=None, generate_normals: bool=True):
    """Construct geometry from mesh file
    
    Can specify byte server if it is a big mesh and needs uri bytes
    """
    
    # Create meshio mesh object to extract data from file, if unsupported file type use meshlab
    try: 
        mesh = meshio.read(file)
    except:
        return meshlab_load(server, byte_server, file, material, mesh_name, generate_normals=generate_normals) 

    # Define Meshio helper functions 
    def get_point_attr(mesh, attr: str):
        """Helper to get attribute from mesh object"""

        data = mesh.point_data.get(attr)
        try:
            return data.tolist()
        except:
            return data

    def get_triangles(mesh):
        """Helper to get triangles from mesh object"""

        for cell in mesh.cells:
            if cell.type == "triangle":
                return cell.data.tolist()
        return None
    
    vertices = mesh.points.tolist()
    indices = get_triangles(mesh)

    # I think attribute name is gonna be specific to mesh - how to map to right attribute?
    normals = get_point_attr(mesh, "NORMAL")
    tangents = get_point_attr(mesh, "TANGENT")
    textures = get_point_attr(mesh, "TEXTURE")
    colors = get_point_attr(mesh, "COLOR")

    # Create patch / geometry for point geometry
    patches = []
    patch_info = GeometryPatchInput(
        vertices = vertices, 
        indices = indices, 
        index_type = "TRIANGLES",
        material = material.id,
        normals = normals,
        tangents = tangents,
        textures = textures,
        colors = colors)
    patches.append(build_geometry_patch(server, mesh_name, patch_info, byte_server, generate_normals=generate_normals))
    geometry = server.create_component(nooobs.Geometry, name=mesh_name, patches=patches)

    return geometry
    

def export_mesh(server: Server, geometry: nooobs.Geometry, new_file_name: str, byte_server: ByteServer=None):
    """Export noodles geometry to mesh file
    
    Args:
        server (Server): server to get components from
        geometry (Geometry): geometry to export
        new_file_name (str): name for file being created
        byte_server (ByteServer): server storing bytes if applicable 
    """

    points = []
    indices = []
    point_data = {}
    for patch in geometry.patches:

        # Extract info from patch
        index = patch.indices
        view: nooobs.BufferView = server.get_component(index.view)
        buffer = server.get_component(view.source_buffer)
        inline, uri = buffer.inline_bytes, buffer.uri_bytes
        if inline:
            bytes = inline
        else:
            try:
                bytes = byte_server.get_buffer(uri)
            except:
                raise Exception("No byte server specified for uri byte mesh")

        # Reconstruct indicies from buffer
        raw_indices = np.frombuffer(bytes, dtype=FORMAT_MAP[index.format], count=index.count, offset=index.offset)
        grouped = [list(x) for x in zip(*(iter(raw_indices),) * 3)]
        indices.extend(grouped)        

        # Reconstruct points and attributes from buffer
        i = 0
        attribute_bytes  = bytes[:index.offset]
        while i < len(attribute_bytes):
            for attribute in patch.attributes:
                format = attribute.format
                current_chunk = attribute_bytes[i:i + SIZES[format]]
                attr_name = attribute.semantic
                attr_data = np.frombuffer(current_chunk, dtype=FORMAT_MAP[format]).tolist()
                i += SIZES[format]
                if attr_name == "POSITION":
                    points.append(attr_data)
                else:
                    point_data.setdefault(attr_name,[]).append(attr_data) 

    # Construct mesh and export
    mesh = meshio.Mesh(
        points,
        [("triangle", indices)],
        point_data = point_data)
    mesh.write(new_file_name)


def dot_product(v1, v2):
    """Helper to take dot product"""
    product = 0
    for c1, c2 in zip(v1, v2):
        product += (round(c1, 5) * round(c2, 5))
    return product


def calculate_normals(vertices: list[list], indices: list[list]):
    """TODO"""
    
    # Idea: go through all the triangles, and calculate normal for each one and attach average to each vertex
    print(f"Generating normals for {len(vertices)} vertices")
    normals = {}
    adjacents = {}
    for triangle in indices:

        # Calculate the normal
        v1, v2, v3 = triangle
        p1, p2, p3 = vertices[v1], vertices[v2], vertices[v3]
        vector1 = np.array([p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2]]) #p1 -> p2
        vector2 = np.array([p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2]]) #p1 -> p3
        normal = np.cross(vector1, vector2)

        # Attach normal to each vertex
        for vertex in triangle:
        
            existing_normals = normals.get(vertex)

            # Add in new normals with matching orientation
            if existing_normals:
                if dot_product(existing_normals[0], normal) < 0:
                    existing_normals.append([-x for x in normal])
                    print(f"Mismatching triangle normals @ {vertex}")
                else:
                    existing_normals.append(normal)
            else:
                normals[vertex] = [normal]
            
            # Mark other vertices in triangle as adjacent
            other_vert = [x for x in triangle if x != vertex]
            adjacents.setdefault(vertex, set()).update(other_vert) 

    print(f"Vertices {len(vertices)} vs. Normals {len(normals)}")

    # Find averages
    for vertex, normal_list in normals.items():

        # Calculate average
        average_normal = []
        for component in zip(*normal_list):
            average_normal.append(mean(component))

        # Normalize and set normal to keep track of final average 
        length = sqrt((average_normal[0]**2) + (average_normal[1]**2) + (average_normal[2]**2))
        normals[vertex] = [x / length for x in average_normal]

    # Orient normals to match
    print(f"Vertices {len(vertices)} vs. Normals {len(normals)}")

    center = [mean(x) for x in zip(*vertices)]
    visited = set()
    starting_index = indices[0][0]
    discovered = deque() # (index, neighbor)
    discovered.append((starting_index, starting_index))
    while discovered:
        
        #print(f"Orienting normal {len(visited)}/{len(discovered)}")
        current_index, neighbor = discovered.popleft()
        dot = dot_product(normals[current_index], normals[neighbor])
        if dot < 0: # Flip vector
            normals[current_index] =[-x for x in normals[current_index]]

        for adjacent in adjacents[current_index]:
            if adjacent not in visited and (adjacent, current_index) not in discovered:
                discovered.append((adjacent, current_index))

        visited.add(current_index)

    print(f"Vertices {len(vertices)} vs. Normals {len(normals)}")
    # Find number pointing towards center
    num_inward = 0
    for index, normal in normals.items():
        center_vector = [x - y for x, y in zip(vertices[index], center)]
        if np.dot(normal, center_vector) < 0:
            num_inward += 1

    # If majority are inward invert
    if num_inward > (len(vertices) / 2):
        for normal in normals.values():
            normal = [-x for x in normal]

    print(f"Finished getting normals...\nNum Inward: {num_inward}")
    print(f"Vertices {len(vertices)} vs. Normals {len(normals)}")
    return [normals.get(i, [0,0,0]) for i in range(len(vertices))]
