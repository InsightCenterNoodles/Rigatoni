
import logging

import pytest
import penne

import rigatoni.noodle_objects as nooobs
from tests.clients import base_client, delegate_client, mock_socket
from tests.servers import base_server

logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG
)


def test_ids():
    generic = nooobs.ID(0, 0)
    generic2 = nooobs.ID(0, 0)
    m = nooobs.MethodID(0, 0)
    m1 = nooobs.MethodID(slot=0, gen=0)
    m2 = nooobs.MethodID(slot=0, gen=1)
    m3 = nooobs.MethodID(slot=1, gen=0)
    s = nooobs.SignalID(slot=0, gen=0)
    assert generic == generic2
    assert generic != m
    assert m != generic
    assert m == m1
    assert m != m2
    assert m != m3
    assert m1 != m2
    assert m1 != m3
    assert m2 != m3
    assert s != m
    assert s != generic
    assert str(m) == "MethodID|0/0|"
    assert str(generic) == "ID|0/0|"
    assert m.compact_str() == "|0/0|"
    assert generic.compact_str() == "|0/0|"
    assert m2.compact_str() == "|0/1|"


def test_delegate(base_client):
    x = nooobs.Delegate(client=base_client, id=nooobs.ID(slot=0, gen=0))
    y = nooobs.Delegate(client=base_client, id=nooobs.ID(slot=1, gen=0), name="Test")
    assert str(x) == "No-Name - Delegate - |0/0|"
    assert str(y) == "Test - Delegate - |1/0|"


def test_invoke_id():
    nooobs.InvokeIDType(entity=nooobs.EntityID(slot=0, gen=0))
    with pytest.raises(ValueError):
        nooobs.InvokeIDType(entity=nooobs.EntityID(slot=0, gen=0), table=nooobs.TableID(slot=0, gen=0))
    with pytest.raises(ValueError):
        nooobs.InvokeIDType()


def test_table_init():

    # Test ints
    int_cols = [nooobs.TableColumnInfo(name="test", type="INTEGER")]
    keys = [0, 1, 2]
    data = [[5], [5], [5]]
    nooobs.TableInitData(columns=int_cols, keys=keys, data=data)

    # Test floats
    real_cols = [nooobs.TableColumnInfo(name="test", type="REAL")]
    keys = [0, 1, 2]
    data = [[5.0], [5.0], [5.0]]
    nooobs.TableInitData(columns=real_cols, keys=keys, data=data)

    # Test strings
    str_cols = [nooobs.TableColumnInfo(name="test", type="TEXT")]
    keys = [0, 1, 2]
    data = [["5"], ["5"], ["5"]]
    nooobs.TableInitData(columns=str_cols, keys=keys, data=data)

    # Test Mismatches
    with pytest.raises(ValueError):
        nooobs.TableInitData(columns=int_cols, keys=keys, data=data)
    with pytest.raises(ValueError):
        nooobs.TableInitData(columns=real_cols, keys=keys, data=data)


def test_method(base_client):
    method = base_client.get_delegate("test_method")
    arg_method = base_client.get_delegate("test_arg_method")
    plot = base_client.get_delegate("test_plot")
    table = base_client.get_delegate("test_table")
    entity = base_client.get_delegate("test_entity")
    method.invoke(plot)
    method.invoke(table)
    method.invoke(entity)
    with pytest.raises(ValueError):
        method.invoke(1)
    assert str(method) == "test_method:\n\tNone\n\tReturns: None\n\tArgs:"
    assert str(arg_method) == "test_arg_method:\n\tNone\n\tReturns: None\n\tArgs:\n\t\t" \
                              "x: How far to move in x\n\t\ty: How far to move in y\n\t\tz: How far to move in z"


def test_entity(base_client):
    entity = base_client.get_delegate("test_entity")
    assert entity.show_methods() == "No methods available"
    entity = base_client.get_delegate("test_method_entity")
    assert entity.show_methods() == "-- Methods on test_method_entity --\n--------------------------------------\n" \
                                    ">> test_method:\n\tNone\n\tReturns: None\n\tArgs:"


# noinspection PyTypeChecker
def test_plot(base_client):
    nooobs.Plot(id=nooobs.PlotID(0, 0), simple_plot="True")
    with pytest.raises(ValueError):
        nooobs.Plot(id=nooobs.PlotID(0, 0))
    with pytest.raises(ValueError):
        nooobs.Plot(id=nooobs.PlotID(0, 0), simple_plot="True", url_plot="True")


def test_buffer():
    nooobs.Buffer(id=nooobs.BufferID(0, 0), inline_bytes=b"test")
    with pytest.raises(ValueError):
        nooobs.Buffer(id=nooobs.BufferID(0, 0))
    with pytest.raises(ValueError):
        nooobs.Buffer(id=nooobs.BufferID(0, 0), inline_bytes=b"test", uri_bytes="test")


def test_image():
    nooobs.Image(id=nooobs.ImageID(0, 0), buffer_source=nooobs.BufferID(0, 0))
    with pytest.raises(ValueError):
        nooobs.Image(id=nooobs.ImageID(0, 0))
    with pytest.raises(ValueError):
        nooobs.Image(id=nooobs.ImageID(0, 0), buffer_source=nooobs.BufferID(0, 0), uri_source="www.test.com")


def test_light(caplog):
    nooobs.Light(id=nooobs.LightID(0, 0), color=[0, 0, 0], point=nooobs.PointLight())
    with pytest.raises(ValueError):
        nooobs.Light(id=nooobs.LightID(0, 0), color=[0, 0, 0])
    with pytest.raises(ValueError):
        nooobs.Light(id=nooobs.LightID(0, 0), color=[0, 0, 0, 1], point=nooobs.PointLight(), spot=nooobs.SpotLight())


def test_basic_table_methods(base_client):

    import penne.handlers as handlers

    table = base_client.get_delegate("test_table")
    cols = [{"name": "test", "type": "TEXT"}]
    init_data = {"columns": cols, "keys": [0, 1, 2], "data": [["test"], ["test"], ["test"]]}
    assert hasattr(table, "test_method")

    # Invoke Signals to hit Table methods
    id = base_client.get_delegate_id("noo::tbl_reset")
    handlers.handle(base_client, 33, {"id": id, "context": {"table": table.id}, "signal_data": [init_data]})
    table._on_table_init(init_data, on_done=print)
    table._reset_table(init_data)
    table._remove_rows(keys=[0, 1, 2])
    table._update_rows(keys=[0, 1, 2], rows=[["test"], ["test"], ["test"]])
    table._update_selection({"name": "Test Selection"})
    table.on_update({"blank": "message"})
    table.on_remove({"blank": "message"})

    with pytest.raises(Exception):
        table.subscribe()  # Doesn't have the injected method so will call None-type as method

    assert table.methods_list == [penne.MethodID(slot=0, gen=0)]


def test_get_context(base_server):
    entity = base_server.get_delegate("test_entity")
    table = base_server.get_delegate("test_table")
    plot = base_server.get_delegate("test_plot")
    method = base_server.get_delegate("test_method")

    assert nooobs.get_context(entity) == {"entity": entity.id}
    assert nooobs.get_context(table) == {"table": table.id}
    assert nooobs.get_context(plot) == {"plot": plot.id}
    assert nooobs.get_context(method) is None
