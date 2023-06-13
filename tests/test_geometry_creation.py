import asyncio
import queue

import pytest
import matplotlib.pyplot as plt
import penne

import rigatoni as rig
from rigatoni import Server
from rigatoni.core import default_json_encoder

from tests.clients import run_basic_operations, base_client
from tests.servers import base_server, geometry_server


def test_geometry_server(geometry_server):
    # Callbacks
    def create_sphere():
        client.invoke_method("create_sphere", on_done=new_point_plot)

    def new_point_plot(*args):
        client.invoke_method("create_sphere", on_done=delete_sphere)

    def delete_sphere(*args):
        client.invoke_method("delete_sphere", on_done=shutdown)

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
