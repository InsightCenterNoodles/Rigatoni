"""Module containing logic for maintaining a client connection

Handles new clients and delegates most work to the server object
"""

import asyncio
import functools
from typing import Type
import json

import websockets
from cbor2 import loads, dumps

from rigatoni.core import Server, default_json_encoder
from rigatoni.noodle_objects import Component, StartingComponent
from rigatoni.delegates import Delegate


async def send(websocket, message: list):
    """Send CBOR message using websocket
    
    Args:
        websocket (WebSocketClientProtocol):
            recipient of this data
        message (list):
            message to be sent, in list format
            [id, content, id, content...]
    """
    # Log message in json file
    json_message = json.dumps(message, default=default_json_encoder)
    with open("sample_messages.json", "a") as outfile:
        outfile.write(json_message)

    # Print message and send
    print(f"Sending Message: ID's {message[::2]}")
    await websocket.send(dumps(message))


async def handle_client(websocket, server: Server):
    """Coroutine for handling a client's connection
    
    Receives and delegates message handling to server
    
    args:
        websocket (WebSocketClientProtocol):
            client connection being handled 
        server (Server):
            object for maintaining state of the scene
    """

    # Update state
    server.clients.add(websocket)

    # Handle intro and update client
    raw_intro_msg = await websocket.recv()
    intro_msg = loads(raw_intro_msg)
    client_name = intro_msg[1]["client_name"]
    print(f"Client '{client_name}' Connecting...")
    
    init_message = server.handle_intro()
    await send(websocket, init_message)

    # Listen for method invocation and keep all clients informed
    async for message in websocket:

        # Decode and print raw message
        message = loads(message)
        print(f"Message from client: {message}")

        # Handle the method invocation
        reply = server.handle_invoke(message[1])

        # Send method reply to client
        await send(websocket, reply)

    # Remove client if disconnected
    print(f"Client 'client_name' disconnected")
    server.clients.remove(websocket)


async def start_server(port: int, starting_state: list[StartingComponent],
                       delegates: dict[Type[Component], Type[Delegate]] = None):
    """Main method for maintaining websocket connection and handling new clients

    Args:
        port (int): port to be used by this server
        starting_state (dict): hardcoded starting state for the server
        delegates (dict): mapping of noodles component to delegate object
    """
    if not delegates:
        delegates = {}

    shutdown_event = asyncio.Event()
    server = Server(starting_state, delegates, shutdown_event)
    print(f"Server initialized with objects: {server.components}")

    # Create partial to pass server to handler
    handler = functools.partial(handle_client, server=server)

    print("Starting up Server...")
    async with websockets.serve(handler, "", port):
        while not shutdown_event.is_set():
            await asyncio.sleep(.1)
        # await asyncio.Future()  # run forever
