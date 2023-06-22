"""Helpful methods for assisting with the creation of geometry objects"""
from math import sqrt
from collections import deque
from statistics import mean
from typing import Optional, Tuple
import logging

import numpy as np
import meshio

from .. import noodle_objects as nooobs
from ..core import Server

from .objects import AttributeInput, GeometryPatchInput
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


def _get_format(num_vertices: int) -> str:
    """Helper to get format that can accommodate number of vertices
    
    Args:
        num_vertices (int): number of vertices needed to store in mesh
    """

    if num_vertices < 256:
        return 'U8'
    elif num_vertices < 65536:
        return 'U16'
    else:
        return 'U32'


def _convert_to_rgba(colors: list):
    """Convert list of arbitrary colors to list of RGBA colors

    Used to ensure geometry patch input colors are valid RGBA colors

    Args:
        colors (list): list of colors, each color is a list of 3 or 4 elements

    Returns:
        list: list of RGBA colors

    Raises:
        ValueError: if color does not have 3 or 4 elements
    """
    rgba_colors = []
    for color in colors:
        if len(color) == 3:
            color = list(color) + [1.0]  # Append 1 to represent alpha channel
        elif len(color) != 4:
            raise ValueError("Color must have 3 or 4 elements")

        # Normalize values if they are in the range 0-255
        normalized_color = [c / 255.0 if c > 1.0 else c for c in color]
        rgba_colors.append(normalized_color)

    return rgba_colors


def _set_up_attributes(patch_input: GeometryPatchInput, generate_normals: bool, ordered=True):
    """Constructs attribute info from input type, not used by users
    
    Takes list input and constructs objects that can be used in build_geometry_patch.
    Specifically, it returns a list of AttributeInput objects that have attributes:
    semantic: nooobs.AttributeSemantic
    format: nooobs.Format
    normalized: bool
    offset: Optional[int]
    stride: Optional[int]

    Args:
        patch_input (GeometryPatchInput): stores lists of vertices, indices
            index type, material, and possibly normals, tangents,
            textures, and colors
        generate_normals (bool): calculate normals for mesh or not

    Returns:
        list: list of AttributeInput objects
    """

    # Generate normals if not indicated in input
    if not patch_input.normals and generate_normals:
        if len(patch_input.vertices) > 1024:
            raise ValueError("Mesh is too large to generate normals. Either provide normals as input or set "
                             "generate_normals to False.")
        patch_input.normals = calculate_normals(patch_input.vertices, patch_input.indices, ordered=ordered)

    # Add attribute info based on the input lists
    attribute_info = []
    position = AttributeInput(
        semantic="POSITION",
        format="VEC3",
        normalized=False,
    )
    attribute_info.append(position)

    if patch_input.normals:
        normal = AttributeInput(
            semantic="NORMAL",
            format="VEC3",
            normalized=False,
        )
        attribute_info.append(normal)

    if patch_input.tangents:
        tangent = AttributeInput(
            semantic="TANGENT",
            format="VEC3",
            normalized=False,
        )
        attribute_info.append(tangent)

    if patch_input.textures:
        texture = AttributeInput(
            semantic="TEXTURE",
            format="U16VEC2",
            normalized=True,
        )
        attribute_info.append(texture)

    if patch_input.colors:
        color = AttributeInput(
            semantic="COLOR",
            format="U8VEC4",
            normalized=True,
        )
        attribute_info.append(color)

        # Check color format and correct, values greater than 1 are assumed to be 0-255, default alpha to 1
        patch_input.colors = _convert_to_rgba(patch_input.colors)

    # Use input to get offsets for each attribute
    offset = 0
    for attribute in attribute_info:
        attribute.offset = offset
        offset += SIZES[attribute.format]

    # Use final offset to get stride
    for attribute in attribute_info:
        attribute.stride = offset

    return attribute_info


def _build_geometry_buffer(server: Server, name, patch_input: GeometryPatchInput, index_format: str,
                           attribute_info: list[AttributeInput],
                           byte_server: ByteServer = None) -> Tuple[nooobs.Buffer, int]:
    """Builds a buffer component from attributes and data from geometry input

    Structures bytes by interleaving attributes grouped by vertex, then indices are added to the end.

    Args:
        server (Server): server to create component on
        name (str): name to give component
        patch_input (GeometryPatchInput): lists of attributes and point data
        index_format (str): format the indices should take
        attribute_info (list[AttributeInput]): Info on the attributes, mostly used for formatting
        byte_server (ByteServer): byte server to use if needed
    """

    # Filter out inputs unspecified by user, and group attributes by point
    fields = [patch_input.vertices, patch_input.normals, patch_input.tangents, patch_input.textures, patch_input.colors]
    data = [x for x in fields if x]
    points = zip(*data)

    # Build byte array by iterating through points and their attributes
    buffer_bytes = bytearray(0)
    for point in points:
        for info, attr in zip(point, attribute_info):
            attr_size = FORMAT_MAP[attr.format]
            new_bytes = np.array(info, dtype=attr_size).tobytes(order='C')
            buffer_bytes.extend(new_bytes)

    # Add index bytes to byte array
    index_offset = len(buffer_bytes)
    index_bytes = np.array(patch_input.indices).astype(FORMAT_MAP[index_format]).tobytes(order='C')
    buffer_bytes.extend(index_bytes)

    # Create buffer component using uri bytes if needed
    size = len(buffer_bytes)
    if size > INLINE_LIMIT:
        logging.info(f"Large Mesh: Using URI Bytes")
        uri = byte_server.add_buffer(buffer_bytes)
        buffer = server.create_buffer(name=name, size=size, uri_bytes=uri)
        return buffer, index_offset
    else:
        buffer = server.create_buffer(
            name=name,
            size=size,
            inline_bytes=buffer_bytes
        )
        return buffer, index_offset


def build_geometry_patch(server: Server, name: str, patch_input: GeometryPatchInput,
                         byte_server: ByteServer = None, generate_normals: bool = True,
                         ordered_indices: bool = True) -> nooobs.GeometryPatch:
    """Build a Geometry Patch with related buffers and views

    Buffer bytes are structured by interleaving attributes grouped by vertex, then indices are added to the end.
    Normals are generated by default if they are not provided. If indices are not oriented consistently, ordered_indices
    should be set to False, slowing down the calculation of normals.

    !!! note

        If the mesh is larger than 10Kb, the buffer will attempt to use URI bytes, and an exception will be raised if
        one is not provided.
    
    Args:
        server (Server): server to create components on
        name (str): name for the components
        patch_input (GeometryPatch): input lists with data to create the patch
        byte_server (ByteServer): optional server to use if mesh is larger than 10Kb
        generate_normals (bool): whether to calculate normals for this mesh
        ordered_indices (bool): whether indices are ordered or not, could be clockwise or counter-clockwise, used when
            calculating normals
    """

    # Set up some constants
    vert_count = len(patch_input.vertices)
    index_count = len(patch_input.indices) * len(patch_input.indices[0])
    index_format = _get_format(vert_count)

    # Set up attributes with given lists
    attribute_info = _set_up_attributes(patch_input, generate_normals=generate_normals, ordered=ordered_indices)

    # Build buffer with given lists
    buffer: nooobs.Buffer
    buffer, index_offset = _build_geometry_buffer(server, name, patch_input, index_format, attribute_info, byte_server)

    # Make buffer view component
    buffer_view: nooobs.BufferView = server.create_component(
        nooobs.BufferView,
        name=name,
        source_buffer=buffer.id,
        type="GEOMETRY",
        offset=0,  # What is this? cant always assume 0
        length=buffer.size
    )

    # Create attribute objects from buffer view and attribute info
    attributes = []
    for attribute in attribute_info:
        attr_obj = nooobs.Attribute(view=buffer_view.id, **dict(attribute))
        attributes.append(attr_obj)

    # Make index to describe indices at end of buffer
    index = nooobs.Index(
        view=buffer_view.id,
        count=index_count,
        offset=index_offset,
        format=index_format
    )

    # Finally create patch 
    patch = nooobs.GeometryPatch(
        attributes=attributes,
        vertex_count=vert_count,
        indices=index,
        type=patch_input.index_type,
        material=patch_input.material
    )

    return patch


def build_instance_buffer(server: Server, name: str, matrices: list[nooobs.Mat4]) -> nooobs.Buffer:
    """Build Buffer from Mat4 to Represent Instances
    
    Args:
        server (Server): server to put buffer component on
        name (str): name for the buffer
        matrices (Mat4): instance matrices
    """

    buffer_bytes = np.array(matrices, dtype=np.single).tobytes()

    buffer = server.create_component(
        nooobs.Buffer,
        name=f"Instance buffer for {name}",
        size=len(buffer_bytes),
        inline_bytes=buffer_bytes
    )

    return buffer


def build_entity(server: Server, geometry: nooobs.Geometry, instances: list[list] = None):
    """Build Entity from Geometry

    Helps format buffers for instances. Can get instance matrices easily with create_instances.
    
    Args:
        server (Server): server to build entity component on
        geometry (Geometry): geometry to link entity to
        instances (Mat4): optional instance matrix, can use create_instances to generate

    Returns:
        Entity: newly created entity delegate
    """

    # Set name to match geometry
    name = geometry.name if geometry.name else None

    # Create instance buffer and view if specified
    if instances:
        buffer = build_instance_buffer(server, name, instances)
        buffer_view = server.create_component(
            nooobs.BufferView,
            name=f"Instance View for {name}",
            source_buffer=buffer.id,
            type="UNK",
            offset=0,
            length=buffer.size
        )
        instance = nooobs.InstanceSource(view=buffer_view.id, stride=0, bb=None)
    else:
        instance = None

    # Create render rep and entity from geometry and instances
    rep = nooobs.RenderRepresentation(mesh=geometry.id, instances=instance)
    entity = server.create_component(nooobs.Entity, name=name, render_rep=rep)

    return entity


def create_instances(
        positions: list[list] = None,
        colors: list[list] = None,
        rotations: list[list] = None,
        scales: list[list] = None) -> list[list]:
    """Create new instance matrices for an entity
    
    All lists are optional and will be filled with defaults.
    By default, one instance is created at least.
    Lists are padded out to 4 values. Each matrix is of the form below

    | position | color | rotation | scale |
    |----------|-------|----------|-------|
    | x        | r     | x        | x     |
    | y        | g     | y        | y     |
    | z        | b     | z        | z     |
    | 1        | a     | w        | 1     |

    Args:
        positions (list[Vec3]): positions for each instance
        colors (list[Vec4]): Colors for each instance
        rotations (list[Vec4]): Rotations for each instance
        scales (list[Vec3]): Scales for each instance

    Returns:
        list: list of instance matrices
    """

    def padded(lst: list, default_val: float = 1.0):
        """Helper to pad the lists"""

        lst = list(lst)
        if len(lst) < 4:
            lst += [default_val] * (4 - len(lst))
        return lst

    # Safeguard against None values for input
    if rotations is None:
        rotations = []
    if colors is None:
        colors = []
    if scales is None:
        scales = []

    # If no inputs specified create one default instance
    if not positions:
        positions = [DEFAULT_POSITION]

    # Use the longest input as number of instances
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


def update_entity(server: Server, entity: nooobs.Entity, geometry: nooobs.Geometry = None, instances: list = None):
    """Update an entity with new instances or geometry
    
    Args:
        server (Server): server with entity to update
        entity (Entity): Entity to be updated
        geometry (Geometry): Optional new geometry if that is being changed
        instances (list[Mat4]): Optional new instances if that is changed

    Returns:
        Entity: updated entity

    Raises:
        ValueError: If no geometry is specified and entity has no geometry
    """

    # Get name from entity if applicable
    name = entity.name if entity.name else None

    # Set geometry id based on whether there is new geometry or not
    old_rep = entity.render_rep
    if geometry:
        mesh = geometry.id
    elif old_rep and old_rep.mesh:
        mesh = old_rep.mesh
    else:
        raise ValueError("No geometry specified and entity has no geometry")

    # Build new buffer / view for instances or use existing instances
    if instances:
        buffer = build_instance_buffer(server, name, instances)
        buffer_view = server.create_component(
            nooobs.BufferView,
            name=f"Instance View for {name}",
            source_buffer=buffer.id,
            type="UNK",
            offset=0,
            length=buffer.size
        )
        instance = nooobs.InstanceSource(view=buffer_view.id, stride=0, bb=None)
    else:
        instance = old_rep.instances if old_rep else None

    # Create new render rep for entity and update entity
    rep = nooobs.RenderRepresentation(mesh=mesh, instances=instance)
    entity.render_rep = rep
    server.update_component(entity)

    # Clean up old components with deletes
    if instances and old_rep and old_rep.instances:
        old_instance_buffer = server.get_delegate(old_rep.instances.view).source_buffer
        old_instance_view = old_rep.instances.view
        server.delete_component(old_instance_buffer)
        server.delete_component(old_instance_view)
    if geometry and old_rep:
        server.delete_component(old_rep.mesh, recursive=True)

    return entity


def add_instances(server: Server, entity: nooobs.Entity, instances: list):
    """Adds instances or merges them into existing instances for an entity
    
    Args:
        server (Server): server with entity to update
        entity (Entity): entity to be updated
        instances (list[Mat4]): new instances to be added, can be generated using 
            create_instances()
    """

    # Ensure we're working with an entity that can be rendered
    if not entity.render_rep:
        raise ValueError(f"Entity {entity} has no render representation - could not add instances")

    # Get old instance buffer from entity's render rep
    rep = entity.render_rep
    if rep.instances:  # Need to combine / merge with old instances
        old_view: nooobs.BufferView = server.state[rep.instances.view]
        old_buffer: nooobs.Buffer = server.state[old_view.source_buffer]
        old_instances = np.frombuffer(old_buffer.inline_bytes, dtype=np.single)

        # Combine new and old instances
        combined = np.append(old_instances, instances).tolist()
        instances = combined

    update_entity(server, entity, instances=instances)


# ---------------------------------- Mesh Importing ----------------------------------#

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
                 material: nooobs.Material, mesh_name: Optional[str] = None,
                 generate_normals: bool = True, ordered: bool = False):
    """Use pymeshlab to load types unsupported by meshio

    This method is only called from geometry_from_mesh if needed
    
    Args:   
        server (Server): server to load geometry onto
        byte_server (ByteServer): server to support URI bytes if needed
        file (str, path): file to load mesh from
        material (Material): material to use in geometry
        mesh_name (str): optional name
        generate_normals (bool): whether to calculate normals for the mesh
    """
    import pymeshlab

    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(file)
    mesh = ms.current_mesh()
    # mesh.compute_normal_per_vertex("Simple Average")
    logging.info(f"Finished Loading Mesh...")

    # Extract data from mesh set structure
    vertices = mesh.vertex_matrix().tolist()
    indices = mesh.face_matrix().tolist()
    # normals = mesh.vertex_normal_matrix().tolist() # Look like they could be off
    normals = None
    tangents = None  # TBD
    textures = None  # TBD
    colors = [convert(color) for color in mesh.vertex_color_array().tolist()]

    # Create patch / geometry for point geometry
    patches = []
    patch_info = GeometryPatchInput(
        vertices=vertices,
        indices=indices,
        index_type="TRIANGLES",
        material=material.id,
        normals=normals,
        tangents=tangents,
        textures=textures,
        colors=colors)
    patches.append(build_geometry_patch(server, mesh_name, patch_info, byte_server, generate_normals=generate_normals,
                                        ordered_indices=ordered))
    geometry = server.create_component(nooobs.Geometry, name=mesh_name, patches=patches)

    return geometry


def geometry_from_mesh(server: Server, file, material: nooobs.Material,
                       mesh_name: Optional[str] = None, byte_server: ByteServer = None,
                       generate_normals: bool = True, ordered_indices: bool = True):
    """Construct geometry from mesh file
    
    Can specify byte server if it is a big mesh and needs uri bytes. By default, uses meshio to avoid
    importing pymeshlab if possible. If meshio fails, pymeshlab is used to load the mesh. Meshio supports
    .inp, .msh, .avs, .cgns, .xml, .e, .exo, .f3grid, .h5m, .mdpa, .mesh, .meshb, .med, .bdf, .fem, .nas,
    .vol, .vol.gz, .post, .post.gz, .dato, .dato.gz, .ply, .stl, .svg, .su2, .ugrid, .vtk, .vtu, .wkt, .xdmf,
    and .xmf. If you are looking to use another format, you will have to install pymeshlab.

    By default, this method will calculate normals for the mesh if they are not provided. This can be a relatively
    intense step that will slow down an application. To turn this off, set generate_normals to False. If indices
    are oriented consistently, set ordered_indices to True to improve performance.

    !!! note

        If the mesh is too large (> 1024 vertices) and calculating the normals would be too intense, this method
        will raise an exception, and you should either provide normals or set generate_normals to False.

    !!! note

        If the mesh is larger than 10Kb, the buffer will attempt to use URI bytes, and an exception will be raised if
        one is not provided.

    Args:
        server (Server): server to load geometry onto
        file (str, path): file to load mesh from
        material (Material): material to use in geometry
        mesh_name (str): optional name
        byte_server (ByteServer): server to support URI bytes if needed
        generate_normals (bool): whether to calculate normals for the mesh
        ordered_indices (bool): whether indices are oriented consistently (clockwise or counterclockwise)

    Returns:
        Geometry: newly created geometry delegate
    """

    # Create meshio mesh object to extract data from file, if unsupported file type use meshlab
    try:
        mesh = meshio.read(file)
    except Exception as e:
        return meshlab_load(server, byte_server, file, material, mesh_name, generate_normals=generate_normals,
                            ordered=ordered_indices)

    # Define Meshio helper functions
    def get_point_attr(mesh_obj, attr: str):
        """Helper to get attribute from mesh object"""

        data = mesh_obj.point_data.get(attr)
        try:
            return data.tolist()
        except Exception:
            return data

    def get_triangles(mesh_obj):
        """Helper to get triangles from mesh object"""

        for cell in mesh_obj.cells:
            if cell.type == "triangle":
                return cell.data.tolist()

    vertices = mesh.points.tolist()
    indices = get_triangles(mesh)

    # I think attribute name is going to be specific to mesh - how to map to right attribute?
    normals = get_point_attr(mesh, "NORMAL")
    tangents = get_point_attr(mesh, "TANGENT")
    textures = get_point_attr(mesh, "TEXTURE")
    colors = get_point_attr(mesh, "COLOR")

    # Create patch / geometry for point geometry
    patches = []
    patch_info = GeometryPatchInput(
        vertices=vertices,
        indices=indices,
        index_type="TRIANGLES",
        material=material.id,
        normals=normals,
        tangents=tangents,
        textures=textures,
        colors=colors)
    patches.append(build_geometry_patch(server, mesh_name, patch_info, byte_server,
                                        generate_normals=generate_normals, ordered_indices=ordered_indices))
    geometry = server.create_component(nooobs.Geometry, name=mesh_name, patches=patches)

    return geometry


def export_mesh(server: Server, geometry: nooobs.Geometry, new_file_name: str, byte_server: ByteServer = None):
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
        view: nooobs.BufferView = server.get_delegate(index.view)
        buffer = server.get_delegate(view.source_buffer)
        inline, uri = buffer.inline_bytes, buffer.uri_bytes
        if inline:
            geo_bytes = inline
        else:
            try:
                geo_bytes = byte_server.get_buffer(uri)
            except Exception as e:
                raise ValueError(f"No byte server specified for uri byte mesh: {e}")

        # Reconstruct indices from buffer
        raw_indices = np.frombuffer(geo_bytes, dtype=FORMAT_MAP[index.format], count=index.count, offset=index.offset)
        grouped = [list(x) for x in zip(*(iter(raw_indices),) * 3)]
        indices.extend(grouped)

        # Reconstruct points and attributes from buffer
        i = 0
        attribute_bytes = geo_bytes[:index.offset]
        while i < len(attribute_bytes):
            for attribute in patch.attributes:
                current_chunk = attribute_bytes[i:i + SIZES[attribute.format]]
                attr_name = attribute.semantic
                attr_data = np.frombuffer(current_chunk, dtype=FORMAT_MAP[attribute.format]).tolist()
                i += SIZES[attribute.format]
                if attr_name == "POSITION":
                    points.append(attr_data)
                else:
                    point_data.setdefault(attr_name, []).append(attr_data)

                    # Construct mesh and export
    mesh = meshio.Mesh(
        points,
        [("triangle", indices)],
        point_data=point_data)
    mesh.write(new_file_name)


def dot_product(v1, v2):
    """Helper to take dot product used in thorough normal calculation"""
    product = 0
    for c1, c2 in zip(v1, v2):
        product += (round(c1, 5) * round(c2, 5))
    return product


# Old slow version, uses BFS to orient the normals in the same direction
def calculate_normals_thorough(vertices: list[list], indices: list[list]):
    """Calculate normals for a mesh

    This method should be used if indices in the mesh are not oriented in the same direction. Normals are calculated
    using the average of face normals for each vertex. Then BFS is used to orient the normals in the same direction.

    !!! note
        This method is slow for larger meshes and should be used sparingly.

    Args:
        vertices (list[list]): list of vertices
        indices (list[list]): list of indices

    Returns:
        list[list]: list of normals
    """
    # Idea: go through all the triangles, and calculate normal for each one and attach average to each vertex
    logging.info(f"Generating normals for {len(vertices)} vertices")
    normals = {}
    adjacents = {}
    for triangle in indices:

        # Calculate the normal
        v1, v2, v3 = triangle
        p1, p2, p3 = vertices[v1], vertices[v2], vertices[v3]
        vector1 = np.array([p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]])  # p1 -> p2
        vector2 = np.array([p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]])  # p1 -> p3
        normal = np.cross(vector1, vector2)

        # Attach normal to each vertex
        for vertex in triangle:

            existing_normals = normals.get(vertex)

            # Add in new normals with matching orientation,
            # Assumes normals will be in same direction for adjacent triangles (no sharp points)
            if existing_normals:
                if dot_product(existing_normals[0], normal) < 0:
                    existing_normals.append([-x for x in normal])
                    logging.info(f"Mismatching triangle normals @ {vertex}")
                else:
                    existing_normals.append(normal)
            else:
                normals[vertex] = [normal]

            # Mark other vertices in triangle as adjacent
            other_vert = [x for x in triangle if x != vertex]
            adjacents.setdefault(vertex, set()).update(other_vert)

    logging.info(f"Vertices {len(vertices)} vs. Normals {len(normals)}")

    # Find averages
    for vertex, normal_list in normals.items():

        # Calculate average
        average_normal = []
        for component in zip(*normal_list):
            average_normal.append(mean(component))

        # Normalize and set normal to keep track of final average
        length = sqrt((average_normal[0] ** 2) + (average_normal[1] ** 2) + (average_normal[2] ** 2))
        normals[vertex] = [x / length for x in average_normal]

    # Orient normals to match
    logging.info(f"Vertices {len(vertices)} vs. Normals {len(normals)}")

    center = [mean(x) for x in zip(*vertices)]
    visited = set()
    starting_index = indices[0][0]
    discovered = deque()  # (index, neighbor)
    discovered.append((starting_index, starting_index))
    while discovered:

        # print(f"Orienting normal {len(visited)}/{len(discovered)}")
        current_index, neighbor = discovered.popleft()
        dot = dot_product(normals[current_index], normals[neighbor])
        if dot < 0:  # Flip vector
            normals[current_index] = [-x for x in normals[current_index]]

        for adjacent in adjacents[current_index]:
            if adjacent not in visited and (adjacent, current_index) not in discovered:
                discovered.append((adjacent, current_index))

        visited.add(current_index)

    logging.info(f"Vertices {len(vertices)} vs. Normals {len(normals)}")
    # Find number pointing towards center
    num_inward = 0
    for index, normal in normals.items():
        center_vector = [x - y for x, y in zip(vertices[index], center)]
        if np.dot(normal, center_vector) < 0:
            num_inward += 1

    # If majority are inward invert
    if num_inward > (len(vertices) / 2):
        for key, normal in normals.items():
            normals[key] = [-x for x in normal]

    logging.info(f"Finished getting normals...\nNum Inward: {num_inward}")
    logging.info(f"Vertices {len(vertices)} vs. Normals {len(normals)}")
    return [normals.get(i, [0, 0, 0]) for i in range(len(vertices))]


def calculate_normals(vertices, indices, ordered=True):
    """Calculate normals for a mesh

    By default, assumes indices are oriented in the same direction. If not, normals will be calculated incorrectly.
    If the ordered flag is set to false, a slower more intense method for calculating normals will be used.

    !!! note
        If you are using `build_geometry_patch` or `geometry_from_mesh`, normals will calculated automatically if
        they are not provided

    Args:
        vertices (list[list]): list of vertices
        indices (list[list]): list of indices
        ordered (bool): whether indices are ordered in the same direction

    Returns:
        list[list]: list of normals
    """

    # If indices are not ordered in any way, hand off to thorough method
    if not ordered:
        return calculate_normals_thorough(vertices, indices)

    # Cast vertices and indices to numpy arrays
    vertices = np.array(vertices).astype(np.float64)
    indices = np.array(indices)

    # Initialize an empty array for vertex normals
    vertex_normals = np.zeros_like(vertices)

    # Iterate over each face
    for face_indices in indices:
        # Get the vertices of the face
        face_vertices = vertices[face_indices]

        # Calculate the face normal using cross product
        edge1 = face_vertices[1] - face_vertices[0]
        edge2 = face_vertices[2] - face_vertices[0]
        face_normal = np.cross(edge1, edge2)

        # Add the face normal to each vertex normal adjacent to the face
        vertex_normals[face_indices] += face_normal

    # Normalize the vertex normals
    magnitudes = np.linalg.norm(vertex_normals, axis=1)
    vertex_normals /= magnitudes[:, np.newaxis]

    # Check how many are facing center and flip if majority is inward
    dot_prods = np.sum(vertex_normals * vertices, axis=1)
    num_inward = np.sum(dot_prods < 0)
    if num_inward > (len(vertices) / 2):
        vertex_normals = -vertex_normals

    return vertex_normals.tolist()
