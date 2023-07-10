
import pytest
import pandas as pd

from rigatoni import *
from .examples.basic_server import CustomTableDelegate, new_point_plot, subscribe, insert, update, remove, clear, update_selection
from .examples.geometry_server import starting_state as geometry_starting_state


def simple_method(server: Server, context, *args):
    return "Method on server called!"


def move_method(server: Server, context, x, y, z):
    print(f"Moving {x}, {y}, {z}")
    return "Moved!"


def throw_exception(server: Server, context: dict, args: list):
    raise MethodException(-32603, "Internal Error")


def internal_error(server: Server, context, *args):
    raise Exception("Expected Exception from testing")


server_delegates = {
    Table: CustomTableDelegate
}


test_args = [
    MethodArg(name="x", doc="How far to move in x", editor_hint="noo::real"),
    MethodArg(name="y", doc="How far to move in y", editor_hint="noo::real"),
    MethodArg(name="z", doc="How far to move in z", editor_hint="noo::real")
]


starting_components = [
    StartingComponent(Method, {"name": "test_method"}, simple_method),
    StartingComponent(Method, {"name": "test_arg_method", "arg_doc": [*test_args]}, move_method),
    StartingComponent(Method, {"name": "new_point_plot", "arg_doc": []}, new_point_plot),
    StartingComponent(Method, {"name": "noo::tbl_subscribe", "arg_doc": []}, subscribe),
    StartingComponent(Method, {"name": "noo::tbl_insert", "arg_doc": []}, insert),
    StartingComponent(Method, {"name": "noo::tbl_update", "arg_doc": []}, update),
    StartingComponent(Method, {"name": "noo::tbl_remove", "arg_doc": []}, remove),
    StartingComponent(Method, {"name": "noo::tbl_clear", "arg_doc": []}, clear),
    StartingComponent(Method, {"name": "noo::tbl_update_selection", "arg_doc": []}, update_selection),
    StartingComponent(Method, {"name": "Test Method 4", "arg_doc": []}, print),
    StartingComponent(Method, {"name": "Bad Method", "arg_doc": []}, throw_exception),
    StartingComponent(Method, {"name": "Internal Error", "arg_doc": []}, internal_error),

    StartingComponent(Signal, {"name": "noo::tbl_reset", "arg_doc": []}),
    StartingComponent(Signal, {"name": "noo::tbl_updated", "arg_doc": []}),
    StartingComponent(Signal, {"name": "noo::tbl_rows_removed", "arg_doc": []}),
    StartingComponent(Signal, {"name": "noo::tbl_selection_updated", "arg_doc": []}),
    StartingComponent(Signal, {"name": "test_signal", "arg_doc": []}),

    StartingComponent(Entity, {"name": "test_entity"}),
    StartingComponent(Entity, {"name": "test_method_entity", "methods_list": [[0, 0]]}),
    StartingComponent(Material, {"name": "test_material"}),
    StartingComponent(Table, {"name": "test_table", "methods_list": [[0, 0]], "signals_list": [[0, 0]]}),
    StartingComponent(Plot, {"name": "test_plot", "simple_plot": "True", "methods_list": [[0, 0]]})
]


@pytest.fixture
def base_server():
    with Server(50000, starting_components, server_delegates) as server:
        yield server


plain_start = [StartingComponent(Table, {"name": "test_table", "methods_list": [[0, 0]], "signals_list": [[0, 0]]})]


@pytest.fixture
def plain_server():
    with Server(50001, starting_state=plain_start) as server:
        yield server


@pytest.fixture
def geometry_server():
    with Server(50002, geometry_starting_state) as server:
        yield server
