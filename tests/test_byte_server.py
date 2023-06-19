import time
import pytest
import urllib.request

import rigatoni as rig


def test_server_basics():

    # Test initialization and adding buffers
    server = rig.ByteServer(8000)
    uri = server.add_buffer(b"test")
    assert server.buffers["0"] == b"test"
    assert isinstance(uri, str)

    # Test retrieval
    buffer = server.get_buffer(uri)
    assert buffer == b"test"
    with pytest.raises(ValueError):
        server.get_buffer("bad_uri")

    # Test connection
    with urllib.request.urlopen(uri) as response:
        response_bytes = response.read()
        assert response_bytes == b"test"

    # Test bad request
    with pytest.raises(urllib.error.HTTPError):
        bad_uri = uri + "bad"
        with urllib.request.urlopen(bad_uri) as response:
            response = response.read()
            assert response_bytes == b"test"

    server.shutdown()

