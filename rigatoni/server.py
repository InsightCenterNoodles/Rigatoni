"""Module containing logic for maintaining a client connection

Handles new clients and delegates most work to the server object
"""

import asyncio
import functools
from typing import Type

import websockets
from cbor2 import loads, dumps

from rigatoni.core import Server
from rigatoni.noodle_objects import Component
from rigatoni.interface import Delegate

async def send(websocket, message: list):
    """Send CBOR message using websocket
    
    Args:
        websocket (WebSocketClientProtocol):
            recipient of this message
        message (list):
            message to be sent, in list format
            [id, content, id, content...]
    """
    
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


async def start_server(port: int, starting_state: dict, 
    delegates: dict[Type[Component], Type[Delegate]] = {}):
    """Main method for maintaining websocket connection and handling new clients

    Args:
        port (int): port to be used by this server
        methods (dict): map containing methods to be injected onto the server
        starting_state (dict): hardcoded starting state for the server
        delegates (dict): mapping of noodles component to delegate object
    """

    server = Server(starting_state, delegates)
    print(f"Server initialized with objects: {server.components}")

    # Create partial to pass server to handler
    handler = functools.partial(
        handle_client,
        server = server
    )

    print("Starting up Server...")
    async with websockets.serve(handler, "", port):
        await asyncio.Future()  # run forever
