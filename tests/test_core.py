import asyncio

import pytest
import penne

import rigatoni as rig
from rigatoni import Server
from rigatoni.core import default_json_encoder

from tests.clients import run_basic_operations, base_client
from tests.servers import base_server


def test_server_init(base_server):

    assert isinstance(base_server, Server)
    assert base_server.port == 50000
    assert len(base_server.state) == 20
    assert base_server.shutdown_event.is_set() is False
    assert base_server.ready.is_set() is True


def test_table_integration(base_server):
    run_basic_operations(penne.TableID(1, 0), plotting=False)


def test_default_json_encoder():
    value = 10
    expected_result = "10"
    assert default_json_encoder(value) == expected_result

    value = "Hello, World!"
    expected_result = "Hello, World!"
    assert default_json_encoder(value) == expected_result

    value = [1, 2, 3]
    expected_result = "[1, 2, 3]"
    assert default_json_encoder(value) == expected_result

    value = {"key": "value"}
    expected_result = "{'key': 'value'}"
    assert default_json_encoder(value) == expected_result


def test_starting_components():

    completely_wrong = [rig.StartingComponent("bad", {}, "bad")]
    bad_args = [rig.StartingComponent(rig.Method, {}, "bad")]
    no_method = [rig.StartingComponent(rig.Method, {"name": "test"})]
    with pytest.raises(TypeError):
        Server(50000, starting_state=completely_wrong)

    with pytest.raises(TypeError):
        Server(50000, starting_state=bad_args)

    with pytest.raises(ValueError):
        Server(50000, starting_state=no_method)


def test_json_logging():

    starting_state = [
        rig.StartingComponent(rig.Entity, {"name": "test_entity"}),
        rig.StartingComponent(rig.Entity, {"name": "test_two", "tags": ["test_tag"]})
    ]

    with Server(50000, starting_state=starting_state, json_output="message_log.json") as server:
        with penne.Client("ws://localhost:50000", strict=True) as client:
            with open(server.json_output, "r") as f:
                assert f.read() == 'JSON Log\n'\
                                   '[4, {"id": [0, 0], "name": "test_entity"}]\n'\
                                   '[4, {"id": [1, 0], "name": "test_two", "tags": ["test_tag"]}]\n' \
                                   '[4, {"id": [1, 0], "name": "test_two", "tags": ["test_tag"]}, 4, {"id": [0, 0], ' \
                                   '"name": "test_entity"}, 31, {"methods_list": [], "signals_list": []}, 35, {}]\n'

            server.broadcast([0, {"id": [0, 0], "name": "test_method"}])
            with open(server.json_output, "r") as f:
                assert f.read() == 'JSON Log\n'\
                                   '[4, {"id": [0, 0], "name": "test_entity"}]\n'\
                                   '[4, {"id": [1, 0], "name": "test_two", "tags": ["test_tag"]}]\n' \
                                   '[4, {"id": [1, 0], "name": "test_two", "tags": ["test_tag"]}, 4, {"id": [0, 0], ' \
                                   '"name": "test_entity"}, 31, {"methods_list": [], "signals_list": []}, 35, {}]\n' \
                                   '[0, {"id": [0, 0], "name": "test_method"}]\n'
            # Go back and fix strings to reflect broadcast and client connect message
            loop = asyncio.get_event_loop()
            loop.run_until_complete(server._send(server.clients.pop(), [2, "test"]))
            with open(server.json_output, "r") as f:
                assert f.read() == 'JSON Log\n'\
                                   '[4, {"id": [0, 0], "name": "test_entity"}]\n'\
                                   '[4, {"id": [1, 0], "name": "test_two", "tags": ["test_tag"]}]\n' \
                                   '[4, {"id": [1, 0], "name": "test_two", "tags": ["test_tag"]}, 4, {"id": [0, 0], ' \
                                   '"name": "test_entity"}, 31, {"methods_list": [], "signals_list": []}, 35, {}]\n' \
                                   '[0, {"id": [0, 0], "name": "test_method"}]\n'\
                                   '[2, "test"]\n'


def test_get_delegate_id(base_server):

    assert base_server.get_delegate_id("test_method") == rig.MethodID(0, 0)
    assert base_server.get_delegate_id("new_point_plot") == rig.MethodID(2, 0)
    assert base_server.get_delegate_id("test_signal") == rig.SignalID(4, 0)
    assert base_server.get_delegate_id("test_entity") == rig.EntityID(0, 0)
    assert base_server.get_delegate_id("test_method_entity") == rig.EntityID(1, 0)
    with pytest.raises(ValueError):
        base_server.get_delegate_id("bad")


def test_get_delegate(base_server):

    assert base_server.get_delegate("test_method") == base_server.get_delegate(rig.MethodID(0, 0))
    assert base_server.get_delegate("test_entity") == base_server.get_delegate({"entity": rig.EntityID(0, 0)})
    with pytest.raises(TypeError):
        base_server.get_delegate(0)
    with pytest.raises(ValueError):
        base_server.get_delegate("bad")


def test_get_delegate_by_context(base_server):
    assert base_server.get_delegate_by_context({"entity": rig.EntityID(0, 0)}) == base_server.get_delegate("test_entity")
    assert base_server.get_delegate_by_context({"table": rig.TableID(0, 0)}) == base_server.get_delegate("test_table")
    assert base_server.get_delegate_by_context({"plot": rig.PlotID(0, 0)}) == base_server.get_delegate("test_plot")
    with pytest.raises(AttributeError):
        base_server.get_delegate_by_context(0)
    with pytest.raises(ValueError):
        base_server.get_delegate_by_context({"bad": rig.MethodID(0, 0)})


def test_get_message_contents(base_server):

    obj = base_server.get_delegate("test_method")
    assert base_server._get_message_contents("create", obj) == {"id": rig.MethodID(0, 0), "name": "test_method", "arg_doc": []}
    assert base_server._get_message_contents("delete", obj) == {"id": rig.MethodID(0, 0)}
    obj.name = "new_name"
    assert base_server._get_message_contents("update", obj, delta={"name"}) == {"id": rig.MethodID(0, 0), "name": "new_name"}
    with pytest.raises(Exception):
        base_server._get_message_contents("delete", 0)
    assert base_server._get_message_contents("bad", obj) == {}


def test_handle_invoke(base_server):

    reply = base_server._handle_invoke({"method": [0, 0], "invoke_id": "0", "args": []})
    assert reply == (34, {'invoke_id': '0', 'result': 'Method on server called!'})

    reply = base_server._handle_invoke({"method": [0, 1], "invoke_id": "0", "args": []})
    assert reply == (34, {'invoke_id': '0', 'method_exception': {"code": -32601, "message": "Method Not Found", "data": None}})

    reply = base_server._handle_invoke({"method": [0, 0], "invoke": "0", "args": [1]})
    assert reply == (34, {'invoke_id': '-1', 'method_exception': {"code": -32700, "message": "Parse Error", "data": None}})


def test_update_references(base_server):

    # Basic Reference
    table_id = base_server.get_delegate_id("test_table")
    plot = base_server.create_plot("Update_Plot", table_id, simple_plot="...")
    assert table_id in base_server.references and base_server.references[table_id] == {plot.id}

    # Remove Reference from delete
    base_server.delete_component(plot)
    assert base_server.references[table_id] == set()


def test_get_id(base_server):

    # Basic Get
    assert base_server._get_id(rig.Light) == rig.LightID(0, 0)

    # Test next available queue
    old_light = base_server.create_table("ID_Table")
    old_light_id = old_light.id
    base_server.delete_component(old_light)
    new_light = base_server.create_table("ID_Table")
    assert new_light.id == old_light_id


def test_delete_component(base_server):

    # Test delete for object that is referenced - check queue
    base_server.delete_component(base_server.get_delegate("noo::tbl_reset"))
    assert base_server.delete_queue == {rig.SignalID(0, 0)}

    # Clear out references and try cascading delete
    base_server.delete_component(base_server.get_delegate("test_table"))

    # Test error handling
    with pytest.raises(TypeError):
        base_server.delete_component("bad")


def test_update_component(base_server):

    # Create a plot that references a table
    table_id = base_server.get_delegate_id("test_table")
    plot = base_server.create_plot("Update_Plot", table_id, simple_plot="...")

    # Update the name of the plot
    plot.name = "New_Named_Plot"
    base_server.update_component(plot)
    assert base_server.client_state[plot.id].name == "New_Named_Plot"
    assert base_server.state[plot.id] == plot

    # Update the table it is plotting
    assert base_server.references[table_id] == {plot.id}
    table = base_server.create_table("New_Table")
    plot.table = base_server.get_delegate_id("New_Table")
    base_server.update_component(plot)  # This doesn't seem  to be updating references, need to debug in depth
    assert base_server.client_state[plot.id].table == rig.TableID(1, 0)
    assert base_server.references[table_id] == set()  # old reference should be removed
    assert base_server.references[table.id] == {plot.id}  # new reference should be added

    # Update list of ID's
    entity = base_server.get_delegate("test_method_entity")
    entity.methods_list = [rig.MethodID(0, 0), rig.MethodID(0, 1)]
    base_server.update_component(entity)
    assert entity.methods_list == [rig.MethodID(0, 0), rig.MethodID(0, 1)]
    assert base_server.client_state[entity.id].methods_list == [rig.MethodID(0, 0), rig.MethodID(0, 1)]

    # Test error handling for components that can't update
    with pytest.raises(ValueError):
        method = base_server.get_delegate("test_method")
        base_server.update_component(method)


def test_invoke_signal(base_server):

    signal = base_server.get_delegate("test_signal")
    on_entity = base_server.get_delegate("test_entity")
    on_plot = base_server.get_delegate("test_plot")

    invoke_message = base_server.invoke_signal(signal.id, on_entity)
    assert invoke_message == (33, {'id': rig.SignalID(4, 0), 'context': {'entity': rig.EntityID(0, 0)}, 'signal_data': []})

    invoke_message = base_server.invoke_signal(signal, on_plot)
    assert invoke_message == (33, {'id': rig.SignalID(4, 0), 'context': {'plot': rig.PlotID(0, 0)}, 'signal_data': []})

    with pytest.raises(ValueError):
        base_server.invoke_signal(signal, signal)


def test_create_delegate_methods(base_server):

    method = base_server.create_method("new_method", [])
    assert isinstance(method, rig.Method)

    signal = base_server.create_signal("new_signal")
    assert isinstance(signal, rig.Signal)

    # Need to keep filling out
