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
            loop.run_until_complete(server.send(server.clients.pop(), [2, "test"]))
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
    assert base_server.get_message_contents("create", obj) == {"id": rig.MethodID(0, 0), "name": "test_method", "arg_doc": []}
    assert base_server.get_message_contents("delete", obj) == {"id": rig.MethodID(0, 0)}
    obj.name = "new_name"
    assert base_server.get_message_contents("update", obj, delta={"name"}) == {"id": rig.MethodID(0, 0), "name": "new_name"}
    with pytest.raises(Exception):
        base_server.get_message_contents("delete", 0)
    assert base_server.get_message_contents("bad", obj) == {}


def test_handle_invoke(base_server):

    reply = base_server.handle_invoke({"method": [0, 0], "invoke_id": "0", "args": []})
    assert reply == (34, {'invoke_id': '0', 'result': 'Method on server called!'})

    reply = base_server.handle_invoke({"method": [0, 1], "invoke_id": "0", "args": []})
    assert reply == (34, {'invoke_id': '0', 'method_exception': {"code": -32601, "message": "Method Not Found", "data": None}})

    reply = base_server.handle_invoke({"method": [0, 0], "invoke": "0", "args": [1]})
    assert reply == (34, {'invoke_id': '-1', 'method_exception': {"code": -32700, "message": "Parse Error", "data": None}})


