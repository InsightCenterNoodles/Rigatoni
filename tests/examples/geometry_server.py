"""Test script for testing geometry creation library

Offers sample methods a server could implement using a sphere
"""

import logging
from typing import List, Optional

import pandas as pd
import numpy as np
import matplotlib
from pyrr import Quaternion, Matrix44

import rigatoni
from rigatoni.core import Server
from rigatoni import geometry as geo

# 42 vertices for sphere
vertices = [[-0.000000, -0.500000, -0.000000], [0.361804, -0.223610, 0.262863],
            [-0.138194, -0.223610, 0.425325], [-0.447213, -0.223608, -0.000000],
            [-0.138194, -0.223610, -0.425325], [0.361804, -0.223610, -0.262863],
            [0.138194, 0.223610, 0.425325], [-0.361804, 0.223610, 0.262863],
            [-0.361804, 0.223610, -0.262863], [0.138194, 0.223610, -0.425325],
            [0.447213, 0.223608, -0.000000], [-0.000000, 0.500000, -0.000000],
            [-0.081228, -0.425327, 0.249998], [0.212661, -0.425327, 0.154506],
            [0.131434, -0.262869, 0.404506], [0.425324, -0.262868, -0.000000],
            [0.212661, -0.425327, -0.154506], [-0.262865, -0.425326, -0.000000],
            [-0.344095, -0.262868, 0.249998], [-0.081228, -0.425327, -0.249998],
            [-0.344095, -0.262868, -0.249998], [0.131434, -0.262869, -0.404506],
            [0.475529, 0.000000, 0.154506], [0.475529, 0.000000, -0.154506],
            [-0.000000, 0.000000, 0.500000], [0.293893, 0.000000, 0.404508],
            [-0.475529, 0.000000, 0.154506], [-0.293893, 0.000000, 0.404508],
            [-0.293893, 0.000000, -0.404508], [-0.475529, 0.000000, -0.154506],
            [0.293893, 0.000000, -0.404508], [-0.000000, 0.000000, -0.500000],
            [0.344095, 0.262868, 0.249998], [-0.131434, 0.262869, 0.404506],
            [-0.425324, 0.262868, -0.000000], [-0.131434, 0.262869, -0.404506],
            [0.344095, 0.262868, -0.249998], [0.081228, 0.425327, 0.249998],
            [0.262865, 0.425326, -0.000000], [-0.212661, 0.425327, 0.154506],
            [-0.212661, 0.425327, -0.154506], [0.081228, 0.425327, -0.249998]]

# 80 triangles
indices = [[0, 13, 12], [1, 13, 15], [0, 12, 17], [0, 17, 19],
           [0, 19, 16], [1, 15, 22], [2, 14, 24], [3, 18, 26],
           [4, 20, 28], [5, 21, 30], [1, 22, 25], [2, 24, 27],
           [3, 26, 29], [4, 28, 31], [5, 30, 23], [6, 32, 37],
           [7, 33, 39], [8, 34, 40], [9, 35, 41], [10, 36, 38],
           [38, 41, 11], [38, 36, 41], [36, 9, 41], [41, 40, 11],
           [41, 35, 40], [35, 8, 40], [40, 39, 11], [40, 34, 39],
           [34, 7, 39], [39, 37, 11], [39, 33, 37], [33, 6, 37],
           [37, 38, 11], [37, 32, 38], [32, 10, 38], [23, 36, 10],
           [23, 30, 36], [30, 9, 36], [31, 35, 9], [31, 28, 35],
           [28, 8, 35], [29, 34, 8], [29, 26, 34], [26, 7, 34],
           [27, 33, 7], [27, 24, 33], [24, 6, 33], [25, 32, 6],
           [25, 22, 32], [22, 10, 32], [30, 31, 9], [30, 21, 31],
           [21, 4, 31], [28, 29, 8], [28, 20, 29], [20, 3, 29],
           [26, 27, 7], [26, 18, 27], [18, 2, 27], [24, 25, 6],
           [24, 14, 25], [14, 1, 25], [22, 23, 10], [22, 15, 23],
           [15, 5, 23], [16, 21, 5], [16, 19, 21], [19, 4, 21],
           [19, 20, 4], [19, 17, 20], [17, 3, 20], [17, 18, 3],
           [17, 12, 18], [12, 2, 18], [15, 16, 5], [15, 13, 16],
           [13, 0, 16], [12, 14, 2], [12, 13, 14], [13, 1, 14]]


class EntityDelegate(rigatoni.Entity):
    """Custom Entity that stores scale, rotation, and position as attributes"""
    scale: Optional[List[float]] = [1.0, 1.0, 1.0]
    rotation: Optional[List[float]] = [0.0, 0.0, 0.0, 1.0]
    position: Optional[List[float]] = [0.0, 0.0, 0.0]

    def update_transform(self):
        transform = np.eye(4)
        transform[3, :3] = self.position
        transform[:3, :3] = Quaternion(self.rotation).matrix33.tolist()
        transform[:3, :3] *= self.scale
        return transform.flatten().tolist()


def move(server: rigatoni.Server, context, vec):
    entity = server.get_delegate(context)
    entity.position = vec
    entity.update_transform()
    server.update_component(entity)


def rotate(server: rigatoni.Server, context, quat):
    entity = server.get_delegate(context)
    # entity.rotation = quat
    # entity.update_transform()
    # server.update_component(entity)

    if sphere.transform is not None:

        # Extract old components of the transform
        old_transform = np.array(sphere.transform).reshape(4, 4)
        old_rotation = old_transform[:3, :3]
        old_translation = old_transform[3, :3]
        old_scale = np.linalg.norm(old_rotation, axis=1)
        scaling_matrix = np.diag(old_scale)

        # Apply rotation to existing transform
        new_rotation = quat.matrix33
        old_rotation /= np.linalg.norm(old_rotation, axis=1)
        new_transform = np.eye(4)
        new_transform[:3, :3] = np.matmul(scaling_matrix, new_rotation)
        new_transform[3, :3] = old_translation
        sphere.transform = new_transform.flatten().tolist()

    else:
        # Flatten to 1d array (col major order) and convert to list
        sphere.transform = quat.matrix44.flatten().tolist()
    server.update_component(sphere)


def scale(server: rigatoni.Server, context, *args):
    entity = server.get_delegate(context)
    x, y, z = args[0]
    if entity.transform is None:
        entity.transform = [x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1]
    else:
        # Something here... as long as its just repeated scaling its ok, rotation in the mix throws things off
        old_transform = np.array(entity.transform).reshape(4, 4)
        new_transform = old_transform

        # Extract old components of the transform, scale and rotation without scaling
        old_scaling_matrix = np.diag(np.linalg.norm(old_transform[:3, :3], axis=1))
        inverse_old_scales = np.linalg.inv(old_scaling_matrix)
        old_rotation = np.matmul(old_transform[:3, :3], inverse_old_scales)

        # Apply new scaling
        new_scaling_matrix = np.diag(np.array([x, y, z]))
        new_transform[:3, :3] = np.matmul(new_scaling_matrix, old_rotation)

        # check = old_transform[:3, :3] / current_scales
        # rotation = old_transform[:3, :3]
        # rotation[0] /= current_scales[0]
        # rotation[1] /= current_scales[1]
        # rotation[2] /= current_scales[2]
        # old_transform[:3, :3] = np.matmul(scaling_matrix, rotation)
        entity.transform = new_transform.flatten().tolist()
    server.update_component(entity)


def delete(server: rigatoni.Server, context, *args):
    sphere = server.get_delegate(context)
    server.delete_component(sphere)

    return 0


def create_spheres(server: rigatoni.Server, context, *args):
    """Test method to create two spheres"""

    name = "Test Sphere"
    # uri_server = rigatoni.ByteServer(port=40000)
    material = server.create_component(rigatoni.Material, name="Test Material")

    # Create Patch
    patches = []
    patch_info = geo.GeometryPatchInput(
        vertices=vertices,
        indices=indices,
        index_type="TRIANGLES",
        material=material.id
    )
    patches.append(geo.build_geometry_patch(server, name, patch_info))

    # Create geometry using patches
    sphere = server.create_component(rigatoni.Geometry, name=name, patches=patches)

    # Set instances and create an entity
    instances = geo.create_instances(
        positions=[(0, 0, 0, 0), (2, 2, 2, 2)],
        colors=[(1.0, .5, .5, 1.0)],
    )
    entity = geo.build_entity(server, geometry=sphere, instances=instances)
    entity.methods_list = [
        server.get_delegate_id("noo::set_position"),
        server.get_delegate_id("noo::set_rotation"),
        server.get_delegate_id("noo::set_scale"),
        server.get_delegate_id("delete")
    ]
    server.update_component(entity)
    geo.export_mesh(server, sphere, "tests/mesh_data/test_sphere.obj")

    # Add Lighting
    point_info = rigatoni.PointLight(range=-1)
    mat = [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        3, 3, 3, 1
    ]
    light = server.create_component(rigatoni.Light, name="Test Point Light", point=point_info)
    # light2 = server.create_component(rigatoni.Light, name="Sun", intensity=5, directional=rigatoni.DirectionalLight())
    #server.create_component(rigatoni.Entity, transform=mat, lights=[light.id])

    spot_info = rigatoni.SpotLight()
    mat = [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 0, 3, 1
    ]
    spot = server.create_component(rigatoni.Light, name="Test Spot Light", spot=spot_info)
    #server.create_component(rigatoni.Entity, transform=mat, lights=[spot.id])

    direction_info = rigatoni.DirectionalLight()
    mat = [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        0, 5, 0, 1
    ]
    directional = server.create_component(rigatoni.Light, name="Test Spot Light", directional=direction_info)
    #server.create_component(rigatoni.Entity, transform=mat, lights=[directional.id])

    return 1


def create_new_instance(server: rigatoni.Server, context, entity_id: list[int], position=None, color=None,
                        rotation=None, scale=None):
    """Method to test instance updating"""

    entity = server.get_delegate(rigatoni.EntityID(*entity_id))
    new_instance = geo.create_instances(position, color, rotation, scale)
    geo.add_instances(server, entity, new_instance)


def normalize_df(df: pd.DataFrame):
    """Helper to normalize values in a dataframe"""

    normalized_df = df.copy()
    for column in normalized_df:
        normalized_df[column] = (df[column] - df[column].min()) / (df[column].max() - df[column].min())

    return normalized_df


def make_point_plot(server: rigatoni.Server, context, *args):
    """Test Method to generate plot-like render from data.csv"""

    name = "Test Plot"
    material = server.create_component(rigatoni.Material, name="Test Material")

    # Add Lighting
    point_info = rigatoni.PointLight(range=-1)
    mat = [
        1, 0, 0, 0,
        0, 1, 0, 0,
        0, 0, 1, 0,
        3, 3, 3, 1
    ]
    light = server.create_component(rigatoni.Light, name="Test Point Light", point=point_info)
    sun = server.create_component(rigatoni.Light, name="Sun", intensity=1, directional=rigatoni.DirectionalLight())
    server.create_component(rigatoni.Entity, transform=mat, lights=[light.id])

    # Create patch / geometry for point geometry
    patches = []
    patch_info = geo.GeometryPatchInput(
        vertices=vertices,
        indices=indices,
        index_type="TRIANGLES",
        material=material.id
    )
    patches.append(geo.build_geometry_patch(server, name, patch_info))
    sphere = server.create_component(rigatoni.Geometry, name=name, patches=patches)

    # Read data from data.csv and normalize
    df = pd.read_csv("tests/mesh_data/data.csv")
    df_scaled = normalize_df(df)

    # Positions
    x = list(df_scaled['Total_CNG'].apply(lambda x: x * 5 - 2.5))
    y = list(df_scaled['Total_Elec'].apply(lambda x: x * 5))
    z = list(df_scaled['Elec_price_incentive'].apply(lambda x: x * 5 - 2.5))

    # Colors
    cmap = matplotlib.cm.get_cmap("plasma")
    cols = df_scaled['CNG_price_incentive']
    cols = [cmap(i) for i in cols]

    # Scales
    s = .1
    scls = [(i * s, i * s, i * s, i * s) for i in list(df_scaled['FCI_incentive_amount[CNG]'])]

    # Create instances of sphere to represent csv data in an entity
    instances = geo.create_instances(
        positions=[*zip(x, y, z)],
        colors=cols,
        scales=scls
    )
    entity = geo.build_entity(server, geometry=sphere, instances=instances)
    entity.methods_list = [
        server.get_delegate_id("noo::set_position"),
        server.get_delegate_id("noo::set_rotation"),
        server.get_delegate_id("noo::set_scale"),
        server.get_delegate_id("delete")
    ]
    server.update_component(entity)
    # new_instance = geo.create_instances([[1,1,1]])
    # geo.add_instances(server, entity, new_instance)
    return 0


def create_from_mesh(server: rigatoni.Server, context, *args):
    """Test Method to generate render from mesh"""

    name = "Test Mesh"
    material = server.create_component(rigatoni.Material, name="Test Material")

    # use libraries from mesh option    
    uri_server = rigatoni.ByteServer(port=60000)
    server.byte_server = uri_server
    mesh = geo.geometry_from_mesh(server, "tests/mesh_data/stanford-bunny.obj", material,
                                  name, uri_server, generate_normals=False)
    # mesh = geo.geometry_from_mesh(server, "mesh_data/test_sphere.vtk", material)
    # mesh = geo.geometry_from_mesh(server, "mesh_data/magvort.x3d", material, name, uri_server, generate_normals=False)
    # mesh = geo.geometry_from_mesh(server, "mesh_databoot.obj", material, name, uri_server)

    #instances = geo.create_instances()
    entity = geo.build_entity(server, geometry=mesh)

    # Test export
    geo.export_mesh(server, mesh, "tests/mesh_data/test_mesh.obj", uri_server)
    return 0


# define arg documentation for injected method
instance_args = [
    rigatoni.MethodArg(name="entity id", doc="What're you creating an instance of?", editor_hint="noo::entity_id"),
    rigatoni.MethodArg(name="position", doc="Where are you putting this instance? vec3", editor_hint="noo::array"),
    rigatoni.MethodArg(name="color", doc="What color is this instance? RGBA Vector", editor_hint="noo::array"),
    rigatoni.MethodArg(name="rotation", doc="How is this instance rotated? Vec4", editor_hint="noo::array"),
    rigatoni.MethodArg(name="scale", doc="How is this instance scaled? Vec3", editor_hint="noo::array")
]

move_args = [
    rigatoni.MethodArg(name="position", doc="Where to move to", editor_hint="noo::array")
]

rot_args = [
    rigatoni.MethodArg(name="rotation", doc="How to rotate", editor_hint="noo::array")
]

scale_args = [
    rigatoni.MethodArg(name="scale", doc="How to scale", editor_hint="noo::array")
]

# Define starting state
starting_state = [
    rigatoni.StartingComponent(rigatoni.Method, {"name": "new_point_plot", "arg_doc": []}, make_point_plot, True),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "create_new_instance", "arg_doc": [*instance_args]},
                               create_new_instance),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "create_sphere", "arg_doc": []}, create_spheres, True),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "create_from_mesh", "arg_doc": []}, create_from_mesh, True),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "delete", "arg_doc": []}, delete),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "noo::set_position", "arg_doc": [*move_args]}, move),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "noo::set_rotation", "arg_doc": [*rot_args]}, rotate),
    rigatoni.StartingComponent(rigatoni.Method, {"name": "noo::set_scale", "arg_doc": [*scale_args]}, scale),
]

delegates = {
    rigatoni.Entity: EntityDelegate
}

logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG
)


def main():

    server = Server(50000, starting_state, delegates)
    server.run()


if __name__ == "__main__":
    main()
