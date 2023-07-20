import queue

import pytest
import matplotlib.pyplot as plt
import penne

import rigatoni as rig
import rigatoni.geometry.methods as geo

from tests.clients import run_basic_operations, base_client
from tests.servers import base_server, geometry_server


# Set up simple test mesh for one triangle
vertices = [[0, 0, 0], [1, 0, 0], [1, 1, 0]]
indices = [[0, 1, 2]]
normals = [[0, 0, 1], [0, 0, 1], [0, 0, 1]]
tangents = [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
textures = [[0, 0], [1, 0], [1, 1]]
colors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
material = rig.MaterialID(0, 0)

position_attr = rig.geometry.AttributeInput(semantic="POSITION", format="VEC3", normalized=False, offset=0, stride=44)
normal_attr = rig.geometry.AttributeInput(semantic="NORMAL", format="VEC3", normalized=False, offset=12, stride=44)
tangents_attr = rig.geometry.AttributeInput(semantic="TANGENT", format="VEC3", normalized=False, offset=24, stride=44)
textures_attr = rig.geometry.AttributeInput(semantic="TEXTURE", format="U16VEC2", normalized=True, offset=36, stride=44)
colors_attr = rig.geometry.AttributeInput(semantic="COLOR", format="U8VEC4", normalized=True, offset=40, stride=44)


def test_geometry_server(geometry_server):
    # Callbacks
    def create_sphere():
        client.invoke_method("create_sphere", callback=new_point_plot)

    def new_point_plot(*args):
        client.invoke_method("create_sphere", callback=delete_sphere)

    def delete_sphere(*args):
        client.invoke_method("delete", context={"entity": [0, 0]}, callback=shutdown)

    def shutdown(*args):
        client.is_active = False
        plt.close('all')
        print("Made it to the end!")

    # Main execution loop
    with penne.Client("ws://localhost:50002", on_connected=create_sphere, strict=True) as client:
        while client.is_active:
            try:
                callback_info = client.callback_queue.get(block=False)
            except queue.Empty:
                continue
            print(f"Callback: {callback_info}")
            callback, args = callback_info
            callback(args) if args else callback()

    print(f"Finished Testing")


# Something wrong here need to look at again, traced it to exception in export possibly
# in _mesh.py line 164 throws exception : ValueError('setting an array element with a sequence.
# The requested array has an inhomogeneous shape after 1 dimensions. The detected shape was (17974,) + inhomogeneous part.')"
# Commented out export mesh for now in geometry_server.py
def test_large_mesh(geometry_server):

    # Callbacks
    def create_from_mesh(*args):
        client.invoke_method("create_from_mesh", callback=shutdown)

    def shutdown(*args):
        client.is_active = False
        plt.close('all')
        geometry_server.byte_server.shutdown()
        print("Made it to the end!")

    # Main execution loop
    with penne.Client("ws://localhost:50002", on_connected=create_from_mesh, strict=True) as client:
        while client.is_active:
            try:
                callback_info = client.callback_queue.get(block=False)
            except queue.Empty:
                continue
            print(f"Callback: {callback_info}")
            callback, args = callback_info
            callback(args) if args else callback()

    print(f"Finished Testing")


def test_get_format():

    assert geo._get_format(100) == 'U8'
    assert geo._get_format(500) == 'U16'
    assert geo._get_format(100000) == 'U32'


def test_convert_to_rgba():

    bad_colors = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    assert geo._convert_to_rgba(bad_colors) == [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]

    bad_colors = [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1]]
    assert geo._convert_to_rgba(bad_colors) == [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]

    bad_colors = [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
    assert geo._convert_to_rgba(bad_colors) == [[1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]

    bad_colors = [[.5, .5, .5], [.5, .5, .5], [.5, .5, .5]]
    assert geo._convert_to_rgba(bad_colors) == [[.5, .5, .5, 1], [.5, .5, .5, 1], [.5, .5, .5, 1]]

    with pytest.raises(ValueError):
        bad_colors = [[1, 0], [0, 1], [0, 0]]
        geo._convert_to_rgba(bad_colors)


def test_set_up_attributes(base_server):

    # Everything filled in
    input_obj = rig.geometry.GeometryPatchInput(vertices=vertices, indices=indices, index_type="TRIANGLES",
                                                normals=normals, tangents=tangents, textures=textures, colors=colors,
                                                material=material)
    assert geo._set_up_attributes(input_obj, False) == [position_attr, normal_attr, tangents_attr,
                                                        textures_attr, colors_attr]

    # Just vertices, indices, and colors
    position_attr.stride = 16
    colors_attr.offset, colors_attr.stride = 12, 16
    input_obj = rig.geometry.GeometryPatchInput(vertices=vertices, indices=indices, index_type="TRIANGLES",
                                                colors=colors, material=material)
    assert geo._set_up_attributes(input_obj, False) == [position_attr, colors_attr]


def test_build_geometry_buffer(base_server):

    # Simple example, vertices, indices, and colors
    geo_input = rig.geometry.GeometryPatchInput(vertices=vertices, indices=indices, index_type="TRIANGLES",
                                                colors=colors, material=material)
    attributes = geo._set_up_attributes(geo_input, False)
    buffer, index_offset = geo._build_geometry_buffer(base_server, "test", geo_input, "U8", attributes)
    assert index_offset == 48
    assert buffer.inline_bytes ==b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x01' \
                                 b'\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x01\x00\x00\x80?' \
                                 b'\x00\x00\x80?\x00\x00\x00\x00\x00\x00\x01\x01\x00\x01\x02'
    # b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00     \x01\x00\x00\x01' [0, 0, 0], (1, 0, 0, 1)
    # b'\x00\x00\x80  ? \x00\x00\x00\x00\x00\x00\x00\x00     \x00\x01\x00\x01' [0, 0, 1], (0, 1, 0, 1)
    # b'\x00\x00\x80  ? \x00\x00\x80  ? \x00\x00\x00\x00     \x00\x00\x01\x01' [0, 1, 1], (0, 0, 1, 1)
    # b'\x00\x01\x02'


def test_build_geometry_patch(base_server):
    pass


def test_calculate_normals():

    calculated = geo.calculate_normals(vertices, indices, ordered=True)
    assert calculated == normals
    check = geo.calculate_normals(vertices, indices, ordered=False)
    assert check == normals


def test_build_entity(base_server):

    geometry = base_server.create_geometry(patches=[], name="test_geometry")
    entity = geo.build_entity(base_server, geometry)
    assert entity.name == "test_geometry"
    assert isinstance(entity, rig.Entity)
    assert entity.render_rep.instances is None


def test_create_instances(base_server):

    # For blank args create one default instance
    assert geo.create_instances() == [[0.0, 0.0, 0.0, 1.0],
                                      [1.0, 1.0, 1.0, 1.0],
                                      [0.0, 0.0, 0.0, 1.0],
                                      [1.0, 1.0, 1.0, 1.0]]

    # Create two instances from just colors
    instance_colors = [[1, 0, 0, 1], [0, 1, 0, 1]]
    assert geo.create_instances(colors=instance_colors) == [[0.0, 0.0, 0.0, 1.0],
                                                            [1.0, 0.0, 0.0, 1.0],
                                                            [0.0, 0.0, 0.0, 1.0],
                                                            [1.0, 1.0, 1.0, 1.0],
                                                            [0.0, 0.0, 0.0, 1.0],
                                                            [0.0, 1.0, 0.0, 1.0],
                                                            [0.0, 0.0, 0.0, 1.0],
                                                            [1.0, 1.0, 1.0, 1.0]]

    # Test padding out to 4 values
    instance_colors = [[1, 0, 0], [0, 1, 0]]
    assert geo.create_instances(colors=instance_colors) == [[0.0, 0.0, 0.0, 1.0],
                                                            [1.0, 0.0, 0.0, 1.0],
                                                            [0.0, 0.0, 0.0, 1.0],
                                                            [1.0, 1.0, 1.0, 1.0],
                                                            [0.0, 0.0, 0.0, 1.0],
                                                            [0.0, 1.0, 0.0, 1.0],
                                                            [0.0, 0.0, 0.0, 1.0],
                                                            [1.0, 1.0, 1.0, 1.0]]


def test_update_entity(base_server):

    entity = base_server.get_delegate("test_entity")

    # Raise error if no geometry specified and no default
    with pytest.raises(ValueError):
        geo.update_entity(base_server, entity)

    # Update with geometry
    geometry = base_server.create_geometry(patches=[], name="test_geometry")
    entity = geo.update_entity(base_server, entity, geometry)
    assert entity.render_rep.instances is None
    assert entity.render_rep.mesh == geometry.id

    # Update with instances
    instances = geo.create_instances()
    entity = geo.update_entity(base_server, entity, instances=instances)
    assert entity.render_rep.instances is not None
    assert entity.render_rep.mesh == geometry.id

    # Update with geometry and instances
    new_geometry = base_server.create_geometry(patches=[], name="new_test_geometry")
    instances = geo.create_instances()
    entity = geo.update_entity(base_server, entity, new_geometry, instances)
    assert entity.render_rep.instances is not None
    assert entity.render_rep.mesh == new_geometry.id
    assert geometry.id not in base_server.state


def test_add_instances(base_server):

    # Add to entity with no instances
    instances = geo.create_instances()
    entity = base_server.get_delegate("test_entity")
    geometry = base_server.create_geometry(patches=[], name="test_geometry")
    entity = geo.update_entity(base_server, entity, geometry)
    assert entity.render_rep.instances is None
    assert entity.render_rep.mesh == geometry.id

    geo.add_instances(base_server, entity, instances)
    assert entity.render_rep.instances is not None
    assert entity.render_rep.mesh == geometry.id
    old_size = base_server.get_delegate(entity.render_rep.instances.view).length
    assert old_size == geo.SIZES["MAT4"]

    # Add to entity with existing instances
    new_instances = geo.create_instances(colors=[[1, 0, 0, 1], [0, 1, 0, 1]])
    geo.add_instances(base_server, entity, new_instances)
    assert entity.render_rep.instances is not None
    assert entity.render_rep.mesh == geometry.id
    new_size = base_server.get_delegate(entity.render_rep.instances.view).length
    assert new_size == old_size + geo.SIZES["MAT4"] * 2

    # Check exception handling
    with pytest.raises(ValueError):
        entity = base_server.get_delegate("test_method_entity")
        geo.add_instances(base_server, entity, instances)


def test_geometry_from_mesh(base_server):

    # Load a basic mesh with meshio option
    mat = base_server.get_delegate("test_material")
    mesh = geo.geometry_from_mesh(base_server, "tests/mesh_data/test_sphere.obj", mat, mesh_name="new_mesh")
    assert mesh.name == "new_mesh"
    assert mesh.patches[0].material == mat.id
    assert mesh.id in base_server.state
    assert mesh.id in base_server.client_state


def test_geometry_from_mesh_large(base_server):

    # Load a mesh with meshlab option
    mat = base_server.get_delegate("test_material")
    mesh = geo.geometry_from_mesh(base_server, "tests/mesh_data/box.gltf", mat, mesh_name="gltf_mesh", generate_normals=False)
    assert mesh.name == "gltf_mesh"
    assert mesh.patches[0].material == mat.id
    assert mesh.id in base_server.state
    assert mesh.id in base_server.client_state

    # Exception for calcualting tangents for large mesh
    with pytest.raises(ValueError):
        geo.geometry_from_mesh(base_server, "tests/mesh_data/stanford-bunny.obj", mat, mesh_name="gltf_mesh", generate_normals=True)


def test_export_mesh(base_server):

    # check exception for byte server
    material = base_server.get_delegate("test_material")
    uri_server = rig.ByteServer()
    mesh = geo.geometry_from_mesh(base_server, "tests/mesh_data/stanford-bunny.obj", material,
                                  "name", uri_server, generate_normals=False)
    with pytest.raises(ValueError):
        geo.export_mesh(base_server, mesh, "test_file")

    uri_server.shutdown()
