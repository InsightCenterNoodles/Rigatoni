
import pytest

from rigatoni import Server


@pytest.fixture
def basic_server():

    with Server(50000, []) as server:
        yield server


def test_server_init(basic_server):

    assert isinstance(basic_server, Server)
    assert basic_server.port == 50000
    assert basic_server.components == {}
    assert basic_server.delegates == {}
    assert basic_server.shutdown_event.is_set() is False
