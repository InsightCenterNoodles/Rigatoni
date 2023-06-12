
import pytest
import penne

from rigatoni import Server

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

