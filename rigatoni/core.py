"""Module with core implementation of Server Object"""

from __future__ import annotations
from typing import Type, TypeVar, Literal, Union
import asyncio
import functools
import logging
import threading

import websockets
from cbor2 import loads, dumps
import json

from .noodle_objects import *


# To allow for more flexible type annotation especially in create component
T = TypeVar("T", bound=Delegate)


def default_json_encoder(value):
    return str(value)


class Server(object):
    """Overarching object for managing the state of a NOODLES session

    Handles communication and multiple client connections. The server provides several
    methods for interacting with and creating delegates. These are especially useful for
    defining custom methods that the server will expose to clients. Can be instatiated normally,
    or it can be used as a context manager to automatically start and stop the server while running
    in a new thread.
    
    Attributes:
        port (int):
            port server is running on
        clients (set):
            client connections
        ids (dict): 
            maps object type to slot tracking info (next_slot, on_deck)
        state (dict):
            document's current state, contains all components with component ID as the key
        client_state (dict):
            lagging state to keep track of how up to date clients are
        references (dict):
            maps component ID to all the component ID's that reference it
        delete_queue (set):
            components that are referenced but have been requested to be deleted
        ready (threading.Event):
            event to signal when server is ready to accept connections
        shutdown_event (asyncio.Event):
            event to signal when server is shutting down
        thread (threading.Thread):
            thread server is running on if using context manager
        byte_server (ByteServer):
            slot to store reference to server that serves uri bytes
        json_output (str):
            path to json file to output message logs
        custom_delegates (dict):
            maps component type to delegate class
        id_map (dict):
            maps component type to ID type
        id_decoder (dict):
            maps ID type to base component type, useful for getting base class from ID
        message_map (dict):
            maps action and type to message ID
    """

    def __init__(self, port: int, starting_state: list[StartingComponent],
                 delegate_map: dict[Type[Delegate], Type[Delegate]] = None, json_output: str = None):
        """Constructor
        
        Args:
            port (int):
                port to run server on
            starting_state (list[StartingComponent]):
                list of objects containing the info to create components on initialization
            delegate_map (dict):
                maps noodles component type to instance of delegate class
            json_output (str):
                path to json file to output message logs
        Raises:
            TypeError: invalid arguments to create starting component
            ValueError: no method specified for method starting component
        """

        self.port = port
        self.clients = set()
        self.ids = {}
        self.state = {}
        self.client_state = {}
        self.references = {}
        self.delete_queue = set()
        self.ready = threading.Event()
        self.shutdown_event = asyncio.Event()
        self.thread = None
        self.byte_server = None
        self.json_output = json_output
        if json_output:
            with open(json_output, "w") as outfile:  # Clear out old contents
                outfile.write("JSON Log\n")

        # Set up id's and custom delegates
        self.custom_delegates = delegate_map if delegate_map else {}
        self.id_map = id_map.copy()
        for old, new in self.custom_delegates.items():
            self.id_map[new] = self.id_map.pop(old)
        self.id_decoder = {val: key for key, val in id_map.items()}

        self.message_map = {
            ("create", MethodID): 0,
            ("delete", MethodID): 1,
            ("create", SignalID): 2,
            ("delete", SignalID): 3,
            ("create", EntityID): 4,
            ("update", EntityID): 5,
            ("delete", EntityID): 6,
            ("create", PlotID): 7,
            ("update", PlotID): 8,
            ("delete", PlotID): 9,
            ("create", BufferID): 10,
            ("delete", BufferID): 11,
            ("create", BufferViewID): 12,
            ("delete", BufferViewID): 13,
            ("create", MaterialID): 14,
            ("update", MaterialID): 15,
            ("delete", MaterialID): 16,
            ("create", ImageID): 17,
            ("delete", ImageID): 18,
            ("create", TextureID): 19,
            ("delete", TextureID): 20,
            ("create", SamplerID): 21,
            ("delete", SamplerID): 22,
            ("create", LightID): 23,
            ("update", LightID): 24,
            ("delete", LightID): 25,
            ("create", GeometryID): 26,
            ("delete", GeometryID): 27,
            ("create", TableID): 28,
            ("update", TableID): 29,
            ("delete", TableID): 30,
            ("update", None): 31,
            ("reset", None): 32,
            ("invoke", None): 33,
            ("reply", None): 34,
            ("initialized", None): 35
        }

        # Set up starting state
        for starting_component in starting_state:
            comp_type = starting_component.type
            comp_method = starting_component.method

            try:
                comp = self.create_component(comp_type, **starting_component.component_attrs)
            except Exception as e:
                raise TypeError(f"Invalid arguments to create {comp_type}: {e}")

            if comp_type == Method and comp_method:
                injected = InjectedMethod(self, comp_method)
                setattr(self, comp.name, injected)
            elif comp_type == Method and not comp_method:
                raise ValueError("Method not specified for starting method")

        logging.debug(f"Server initialized with objects: {self.state}")

    def __enter__(self):
        """Enter context manager"""
        self.thread = threading.Thread(target=self.run)
        self.thread.start()
        self.ready.wait()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager"""
        self.shutdown()
        self.thread.join()

    def run(self):
        """Run the server

        This will run indefinitely until the server is shutdown"""
        return asyncio.run(self._start_server())

    async def _start_server(self):
        """Run the server and listen for connections"""

        # Create partial to pass server to handler
        handler = functools.partial(self._handle_client)

        logging.info("Starting up Server...")
        async with websockets.serve(handler, "", self.port):
            self.ready.set()
            while not self.shutdown_event.is_set():
                await asyncio.sleep(.1)

    def shutdown(self):
        """Shuts down the server and closes off communication with clients"""
        logging.info("Shutting down server...")
        self.shutdown_event.set()

    def _log_json(self, message: list):
        json_message = json.dumps(message, default=default_json_encoder)
        formatted_message = f"{json_message}\n"
        with open(self.json_output, "a") as outfile:
            outfile.write(formatted_message)

    async def _send(self, websocket, message: list):
        """Send CBOR message using websocket

        Args:
            websocket (WebSocketClientProtocol):
                recipient of this data
            message (list):
                message to be sent, in list format
                [id, content, id, content...]
        """

        # Log message in json file if applicable
        if self.json_output:
            self._log_json(message)

        # Log message and send
        logging.debug(f"Sending Message: ID's {message[::2]}")
        await websocket.send(dumps(message))

    async def _handle_client(self, websocket):
        """Coroutine for handling a client's connection

        Receives and delegates message handling to server

        args:
            websocket (WebSocketClientProtocol):
                client connection being handled
            server (Server):
                object for maintaining state of the scene
        """

        # Update track of clients
        self.clients.add(websocket)

        # Handle intro and update client
        raw_intro_msg = await websocket.recv()
        intro_msg = loads(raw_intro_msg)
        client_name = intro_msg[1]["client_name"]
        logging.info(f"Client '{client_name}' Connecting...")

        init_message = self._handle_intro()
        await self._send(websocket, init_message)

        # Listen for method invocation and keep all clients informed
        async for message in websocket:
            # Decode and log raw message
            message = loads(message)
            logging.debug(f"Message from client: {message}")

            # Handle the method invocation
            reply = self._handle_invoke(message[1])

            # Send method reply to client
            await self._send(websocket, list(reply))

        # Remove client if disconnected
        logging.debug(f"Client 'client_name' disconnected")
        self.clients.remove(websocket)

    def get_ids_by_type(self, component: Type[Delegate]) -> list:
        """Get all ids for certain component type
        
        Args:
            component (type): type of component to get ID's for

        Returns:
            ids: list of ids for components of specified type
        """

        return [key for key, val in self.state.items() if isinstance(val, component)]

    def get_delegate_id(self, name: str):
        """Get a component by using its name

        Args:
            name (str): name of component to get

        Returns:
            id: id of component with specified name

        Raises:
            ValueError: if no component with specified name is found
        """

        for delegate in self.state.values():
            if delegate.name == name:
                return delegate.id
        raise ValueError("No Component Found")

    def get_delegate(self, identifier: Union[ID, str, Dict[str, ID]]):
        """Access components in state

        Can be called with an ID, name, or context of the delegate

        Args:
            identifier (Union[ID, str, Dict[str, ID]]): identifier for component

        Returns:
            delegate: delegate with specified identifier

        Raises:
            TypeError: if identifier is not of type ID, str, or dict
            ValueError: if no component with specified identifier is found or context is invalid
        """
        if isinstance(identifier, ID):
            return self.state[identifier]
        elif isinstance(identifier, str):
            return self.state[self.get_delegate_id(identifier)]
        elif isinstance(identifier, dict):
            return self.get_delegate_by_context(identifier)
        else:
            raise TypeError(f"Invalid type for identifier: {type(identifier)}")

    def get_delegate_by_context(self, context: dict):
        """Get a component using a context object

        This is especially useful in methods that are invoked in a certain context.

        !!! note

            Contexts are only used when working with entities, tables, and plots.

        Args:
            context (dict): context of the form {str: ID}

        Returns:
            delegate: delegate from specified context

        Raises:
            ValueError: if context is invalid
        """

        entity = context.get("entity")
        table = context.get("table")
        plot = context.get("plot")
        if entity:
            return self.get_delegate(EntityID(*entity))
        elif table:
            return self.get_delegate(TableID(*table))
        elif plot:
            return self.get_delegate(PlotID(*plot))
        else:
            raise ValueError(f"Invalid context: {context}")

    def _get_message_contents(self, action: str, noodle_object: NoodleObject, delta: set[str] = None):
        """Helper to handle construction of message dict
        
        Args:
            action (str): action taken with message
            noodle_object (NoodleObject): Delegate, Reply, or Invoke object
            delta (set): field names to be included in update
        """

        contents = {}
        if action == "create":
            base_delegate = self.id_decoder[type(noodle_object.id)]
            include = {field for field in base_delegate.__fields__ if field not in ["server", "signals"]}
            contents = noodle_object.dict(exclude_none=True, include=include)

        elif action == "invoke":
            contents = noodle_object.dict(exclude_none=True)

        elif action == "reply":

            if noodle_object.method_exception:
                e = noodle_object.method_exception
                contents = noodle_object.dict(exclude_none=True)
                contents["method_exception"] = {"code": e.code, "message": e.message, "data": e.data}
            else:
                contents = noodle_object.dict(exclude_none=True)

        elif action == "update":
            if not noodle_object:  # Document case
                contents["methods_list"] = self.get_ids_by_type(Method)
                contents["signals_list"] = self.get_ids_by_type(Signal)
            else:  # Normal update, include id, and any field in delta
                delta = set() if not delta else delta
                delta.add("id")
                contents = noodle_object.dict(exclude_none=True, include=delta)

        elif action == "delete":
            try:
                contents["id"] = noodle_object.id
            except AttributeError:
                raise Exception(f"Cannot delete a {noodle_object}")

        return contents

    def _prepare_message(self, action: str, noodle_object: NoodleObject = None, delta: set[str] = None):
        """Given object and action, get id and message contents as dict

        Args:
            action (str): action taken with message
            noodle_object (NoodleObject): Component, Reply, or Invoke object
            delta (set): field names to be included in update
        """

        delegate_type = None if not isinstance(noodle_object, Delegate) else type(noodle_object.id)
        key = (action, delegate_type)
        message_id = self.message_map[key]
        contents = self._get_message_contents(action, noodle_object, delta)

        return message_id, contents

    def broadcast(self, message: list):
        """Broadcast message to all connected clients
        
        Args:
            message [tuple]: fully constructed message in form (tag/id, contents)
        """

        # Log message in json file if applicable
        if self.json_output:
            self._log_json(message)

        logging.debug(f"Broadcasting Message: ID's {message[::2]}")
        encoded = dumps(message)
        websockets.broadcast(self.clients, encoded)

    def _handle_intro(self):
        """Formulate response for new client"""

        # Add create message for every object in state
        message = []
        ordered_components = order_components(self.state, self.references)
        for component in ordered_components:
            msg_id, content = self._prepare_message("create", component)
            message.extend([msg_id, content])

        # Add document update
        message.extend(self._prepare_message("update", None))

        # Finish with initialization message
        message.extend(self._prepare_message("initialized"))
        return message

    def _handle_invoke(self, message: dict):
        """Handle all invokes coming from the client
        
        Take message and formulate response for clients. Tries to invoke and
        raises appropriate error codes if unsuccessful. Note that the method 
        technically doesn't raise any exceptions, instead the exception is 
        captured in a message and sent to the client.
        
        Args:
            message (dict): dict form of message from client
        """

        # Create generic reply with invalid invoke ID and attempt invoke
        reply_obj = Reply(invoke_id="-1")
        try:
            self._invoke_method(message, reply_obj)

        except Exception as e:
            if type(e) is MethodException:
                reply_obj.method_exception = e
            else:
                logging.error(f"\033[91mServerside Error from Method: {e}\033[0m")
                reply_obj.method_exception = MethodException(code=-32603, message="Internal Error")

        return self._prepare_message("reply", reply_obj)

    def _invoke_method(self, message: dict, reply: Reply):
        """Invoke method and build out reply object
        
        Mostly a helper for handle_invoke to raise proper method exceptions

        Args:
            message (dict): Invoke message in dict form
            reply (Reply): Practically empty reply object to be updated 
        """

        # Parse message
        try:
            method_id = MethodID(slot=message["method"][0], gen=message["method"][1])
            context = message.get("context")
            invoke_id = message["invoke_id"]
            args: list = message["args"]
            reply.invoke_id = invoke_id
        except Exception:
            raise MethodException(code=-32700, message="Parse Error")

        # Locate method
        try:
            method_name = self.state[method_id].name
            method = getattr(self, method_name)
        except Exception:
            raise MethodException(code=-32601, message="Method Not Found")

        # Invoke
        reply.result = method(context, *args)

    def _update_references(self, parent_delegate: Delegate, current: NoodleObject, removing=False):
        """Update in-degree for all objects referenced by this one

        Recursively updates references for all components under a parent one. Here,
        the current object changes through the recursion while comp keeps track of 
        the parent. Essentially finds all the objects that delegate points to
        
        Args:
            parent_delegate (Delegate): parent component with new references to be tracked
            current (NoodleObject): current object being examined
            removing (bool): flag so function can be used to both add and remove references
        """

        for key, val in current:

            # Found a reference
            if key != "id" and isinstance(val, ID):
                if removing:
                    self.references[val].remove(parent_delegate.id)
                else:
                    self.references.setdefault(val, set()).add(parent_delegate.id)

            # Found another object to recurse on
            elif isinstance(val, NoodleObject):
                self._update_references(parent_delegate, val, removing)

            # Found list of objects or id's to recurse on 
            elif val is not None and isinstance(val, list):

                # Objects
                if len(val) > 0 and isinstance(val[0], NoodleObject):
                    for obj in val:
                        self._update_references(parent_delegate, obj, removing)

                # ID's
                elif len(val) > 0 and isinstance(val[0], ID):
                    for id in val:
                        if removing:
                            self.references[id].remove(parent_delegate.id)
                        else:
                            self.references.setdefault(id, set()).add(parent_delegate.id)

    def _get_id(self, delegate_type: Type[Delegate]) -> ID:
        """Get next open ID
        
        Check for open slots then take the closest available slot

        Args:
            delegate_type (Type): type for desired ID
        """

        # Check if type is already tracked and set it up if not
        if delegate_type in self.ids:
            slot_info = self.ids[delegate_type]
        else:
            slot_info = SlotTracker()
            self.ids[delegate_type] = slot_info

        # Create the new ID from tracked info
        if slot_info.on_deck.empty():
            id_type = self.id_map[delegate_type]
            id = id_type(slot=slot_info.next_slot, gen=0)
            slot_info.next_slot += 1
            return id
        else:
            return slot_info.on_deck.get()

    # Interface methods to build server methods ===============================================

    def create_component(self, comp_type: Type[T], **kwargs) -> T:
        """Officially create new component in state
        
        This method updates state, updates references, and broadcasts msg to clients.
        It also handles the acquisition of a valid ID. This is a general creator method, but
        more specific versions exist for each component type. Keyword arguments should be
        used for specifying the attributes of the component. Any deviation from the spec will
        raise a validation exception.

        !!! note

            Since this method handles the ID, it should not be specified as one of the keyword arguments.
        
        Args:
            comp_type (Component Type): type of component to be created
            **kwargs: the user should specify the attributes of the component using 
                keyword arguments. Refer to the noodle objects to see which attributes
                are required and optional. Any deviation from the spec will raise a 
                validation exception.

        Returns:
            Delegate: delegate for the newly created component

        Raises:
            ValueError: if the user specifies an invalid attribute for the component
        """

        # Get ID and try to create delegate from args
        comp_type = self.custom_delegates.get(comp_type, comp_type)
        comp_id = self._get_id(comp_type)
        try:
            new_delegate = comp_type(server=self, id=comp_id, **kwargs)
        except Exception as e:
            raise ValueError(f"Args: {kwargs}, invalid for initializing a {comp_type}: {e}")

        # Update state and keep track of initial version for changes / update messages
        self.state[comp_id] = new_delegate
        self.client_state[comp_id] = new_delegate.copy()

        # Update references for each component referenced by this one
        self._update_references(new_delegate, new_delegate)

        # Create message and broadcast
        message = self._prepare_message("create", new_delegate)
        self.broadcast(message)

        # Return component or delegate instance if applicable
        return new_delegate

    def delete_component(self, delegate: Union[Delegate, ID], recursive: bool = False):
        """Delete object in state and update clients
        
        This method excepts a delegate, or component ID, and will attempt
        to delete the component as long as it is not referenced by any other component.
        If this component is still being used by another, it will be added to a queue so that
        it can be deleted later once that reference is no longer being used. If recursive flag
        is set, then all components referenced by this one will also be deleted.


        Args:
            delegate (Component, Delegate, or ID): component / delegate to be deleted

        Raises:
            TypeError: if the user specifies an invalid input type
        """

        # Handle cases so can except different input types - cast to ID
        if isinstance(delegate, Delegate):
            delegate = delegate
            del_id = delegate.id
        elif isinstance(delegate, ID):
            delegate = self.state[delegate]
            del_id = delegate.id
        else:
            raise TypeError(f"Invalid type for delegate when deleting: {type(delegate)}")

        # Delete if no references, or else queue it up for later
        if not self.references.get(del_id):
            self.broadcast(self._prepare_message("delete", delegate))
            del self.state[del_id]
            del self.client_state[del_id]

            # Free up the ID
            self.ids[type(delegate)].on_deck.put(del_id)

            # Clean out references from this object
            for refs in self.references.values():
                while del_id in refs:
                    refs.remove(del_id)

            # Check if anything in the queue is now clear to be deleted
            for comp_id in list(self.delete_queue):
                if not self.references.get(comp_id):
                    self.delete_queue.remove(comp_id)
                    self.delete_component(comp_id)

        else:
            logging.warning(f"Couldn't delete {delegate}, referenced by {self.references[del_id]}, added to queue")
            self.delete_queue.add(del_id)

    @staticmethod
    def _find_delta(state, edited):
        """Helper to find differences between two objects
        
        Also checks to find recursive cases and cases where references
        should be updated, Does this get recursive deltas tho? should it?
        """

        delta = set()
        for field_name, value in edited:
            state_val = getattr(state, field_name)
            if value != state_val:
                delta.add(field_name)
        return delta

    def update_component(self, current: Delegate):
        """Update clients with changes to a component
        
        This method broadcasts changes to all clients including only fields
        specified in the set delta. Local changes to delegates will be saved
        in the server's state, but this method must be called to update clients.

        Args:
            current (Delegate): component that has been updated,
                should be a component with an update message
        """

        # Find difference between two states
        outdated = self.client_state[current.id]
        delta = self._find_delta(outdated, current)

        # Update references
        self._update_references(outdated, outdated, removing=True)
        self._update_references(current, current)

        # Update tracking state
        self.client_state[current.id] = current.copy()

        # Form message and broadcast
        try:
            message = self._prepare_message("update", current, delta)
            self.broadcast(message)
        except Exception as e:
            raise ValueError(f"This obj can not be updated: {e}")

    def invoke_signal(self, signal: Union[SignalID, Signal], on_component: Delegate, signal_data: list = None):
        """Send signal to target component
        
        Args:
            signal (ID): signal to be invoked
            on_component (Delegate): component to receive the signal
            signal_data (dict): data to be sent with the signal

        Returns:
            message: message to be broadcast

        Raises:
            ValueError: if the user specifies an invalid on_component type
        """

        # Cast signal to ID if needed
        if isinstance(signal, Signal):
            signal = signal.id

        # Fill in default signal data if not specified
        if signal_data is None:
            signal_data = []

        # Get context from on_component
        if isinstance(on_component, Entity):
            context = InvokeIDType(entity=on_component.id)
        elif isinstance(on_component, Table):
            context = InvokeIDType(table=on_component.id)
        elif isinstance(on_component, Plot):
            context = InvokeIDType(plot=on_component.id)
        else:
            raise ValueError(f"Invalid on_component type: {type(on_component)}")

        # Create invoke object and broadcast message
        invoke = Invoke(id=signal, context=context, signal_data=signal_data)
        message = self._prepare_message("invoke", invoke)
        self.broadcast(message)
        return message

    def create_method(self, name: str,
                      arg_doc: list[MethodArg],
                      doc: Optional[str] = None,
                      return_doc: Optional[str] = None) -> Method:
        """Add a Method object to the scene and return it. Will use a custom delegate if applicable.

        Args:
            name (str): name of the method
            arg_doc (list[MethodArg]): list of arguments and documentation for the method
            doc (str, optional): documentation for the method
            return_doc (str, optional): documentation for the return value

        Returns:
            Method: method delegate that was created
        """
        return self.create_component(Method, name=name, doc=doc, return_doc=return_doc, arg_doc=arg_doc)

    def create_signal(self, name: str,
                      doc: Optional[str] = None,
                      arg_doc: list[MethodArg] = None) -> Signal:
        """Add a Signal object to the session. Will use a custom delegate if applicable.

        Args:
            name (str): name of the signal
            doc (str, optional): documentation for the signal
            arg_doc (list[MethodArg], optional): list of arguments and documentation for the signal

        Returns:
            Signal: signal delegate that was created
        """
        return self.create_component(Signal, name=name, doc=doc, arg_doc=arg_doc)

    def create_entity(self, name: Optional[str],
                      parent: Optional[EntityID] = None,
                      transform: Optional[Mat4] = None,
                      text_rep: Optional[TextRepresentation] = None,
                      web_rep: Optional[WebRepresentation] = None,
                      render_rep: Optional[RenderRepresentation] = None,
                      lights: Optional[list[LightID]] = None,
                      tables: Optional[list[TableID]] = None,
                      plots: Optional[list[PlotID]] = None,
                      tags: Optional[list[str]] = None,
                      methods_list: Optional[list[MethodID]] = None,
                      signals_list: Optional[list[SignalID]] = None,
                      influence: Optional[BoundingBox] = None) -> Entity:
        """Add an Entity object to the session. Will use a custom delegate if applicable.

        Args:
            name (str): name of the entity
            parent (EntityID, optional): parent entity
            transform (Mat4, optional): transform for the entity
            text_rep (TextRepresentation, optional): text representation for the entity
            web_rep (WebRepresentation, optional): web representation for the entity
            render_rep (RenderRepresentation, optional): render representation that links to geometry info
            lights (list[LightID], optional): list of attached lights
            tables (list[TableID], optional): list of attached tables
            plots (list[PlotID], optional): list of attached plots
            tags (list[str], optional): list of applicable tags
            methods_list (list[MethodID], optional): list of methods attached to the entity
            signals_list (list[SignalID], optional): list of signals attached to the entity
            influence (BoundingBox, optional): bounding box for the entity

        Returns:
            Entity: entity delegate that was created
        """
        return self.create_component(Entity, name=name, parent=parent, transform=transform, text_rep=text_rep,
                                     web_rep=web_rep, render_rep=render_rep, lights=lights, tables=tables, plots=plots,
                                     tags=tags, methods_list=methods_list, signals_list=signals_list,
                                     influence=influence)

    def create_plot(self, name: Optional[str] = None,
                    table: Optional[TableID] = None,
                    simple_plot: Optional[str] = None,
                    url_plot: Optional[str] = None,
                    methods_list: Optional[list[MethodID]] = None,
                    signals_list: Optional[list[SignalID]] = None) -> Plot:
        """Add a Plot object to the session. Will use a custom delegate if applicable.

        Args:
            name (str, optional): name of the plot
            table (TableID, optional): table to be plotted
            simple_plot (str, optional): simple plot to be plotted
            url_plot (str, optional): url for the plot
            methods_list (list[MethodID], optional): attached methods
            signals_list (list[SignalID], optional): attached signals

        Returns:
            Plot: plot delegate that was created
        """
        return self.create_component(Plot, name=name, table=table, simple_plot=simple_plot, url_plot=url_plot,
                                     methods_list=methods_list, signals_list=signals_list)

    def create_buffer(self, name: Optional[str] = None,
                      size: int = None,
                      inline_bytes: bytes = None,
                      uri_bytes: str = None) -> Buffer:
        """Add a Buffer object for the session. Will use a custom delegate if applicable.

        Args:
            name (str, optional): name of the buffer, defaults to "No-Name
            size (int, optional): size of the buffer in bytes
            inline_bytes (bytes, optional): bytes for the buffer
            uri_bytes (str, optional): uri to get the bytes from the web

        Returns:
            Buffer: buffer delegate that was created
        """
        return self.create_component(Buffer, name=name, size=size, inline_bytes=inline_bytes, uri_bytes=uri_bytes)

    def create_bufferview(self,
                          source_buffer: BufferID,
                          offset: int,
                          length: int,
                          name: Optional[str] = None,
                          type: Literal["UNK", "GEOMETRY", "IMAGE"] = "UNK") -> BufferView:
        """Add a BufferView object to the session. Will use a custom delegate if applicable.

        Args:
            source_buffer (BufferID): buffer that the view is based on
            offset (int): offset in bytes from the start of the buffer
            length (int): length of the view in bytes
            name (str, optional): name of the buffer view
            type (str, optional): type of the buffer view

        Returns:
            BufferView: buffer view delegate that was created
        """
        return self.create_component(BufferView, name=name, source_buffer=source_buffer,
                                     offset=offset, length=length, type=type)

    def create_material(self, name: Optional[str] = None,
                        pbr_info: Optional[PBRInfo] = PBRInfo(),
                        normal_texture: Optional[TextureRef] = None,
                        occlusion_texture: Optional[TextureRef] = None,
                        occlusion_texture_factor: Optional[float] = 1.0,
                        emissive_texture: Optional[TextureRef] = None,
                        emissive_factor: Optional[Vec3] = (1.0, 1.0, 1.0),
                        use_alpha: Optional[bool] = False,
                        alpha_cutoff: Optional[float] = .5,
                        double_sided: Optional[bool] = False) -> Material:
        """Add a Material object to the session. Will use a custom delegate if applicable.

        Args:
            name (str, optional): name of the material
            pbr_info (PBRInfo, optional): physically based rendering information
            normal_texture (TextureRef, optional): texture for normal mapping
            occlusion_texture (TextureRef, optional): texture for occlusion mapping
            occlusion_texture_factor (float, optional): factor for occlusion mapping
            emissive_texture (TextureRef, optional): texture for emissive mapping
            emissive_factor (Vec3, optional): factor for emissive mapping
            use_alpha (bool, optional): whether to use alpha
            alpha_cutoff (float, optional): alpha cutoff value
            double_sided (bool, optional): whether the material is double-sided

        Returns:
            Material: material delegate that was created
        """
        return self.create_component(Material, name=name, pbr_info=pbr_info, normal_texture=normal_texture,
                                     occlusion_texture=occlusion_texture,
                                     occlusion_texture_factor=occlusion_texture_factor,
                                     emissive_texture=emissive_texture, emissive_factor=emissive_factor,
                                     use_alpha=use_alpha, alpha_cutoff=alpha_cutoff, double_sided=double_sided)

    def create_image(self, name: Optional[str] = None,
                     buffer_source: BufferID = None,
                     uri_source: str = None) -> Image:
        """Add an Image object to the session.

        Will use a custom delegate if applicable. Must specify either a buffer_source or a uri_source.

        Args:
            name (str, optional): name of the image
            buffer_source (BufferID, optional): buffer data that for image
            uri_source (str, optional): uri to get the image bytes from

        Returns:
            Image: image delegate that was created
        """
        return self.create_component(Image, name=name, buffer_source=buffer_source, uri_source=uri_source)

    def create_texture(self, image: ImageID,
                       name: Optional[str] = None,
                       sampler: Optional[SamplerID] = None) -> Texture:
        """Add a Texture object to the session. Will use a custom delegate if applicable.

        Args:
            image (ImageID): image to be used for the texture
            name (str, optional): name of the texture
            sampler (SamplerID, optional): sampler to be used for the texture

        Returns:
            Texture: texture delegate that was created
        """
        return self.create_component(Texture, name=name, image=image, sampler=sampler)

    def create_sampler(self, name: Optional[str] = None,
                       mag_filter: Optional[Literal["NEAREST", "LINEAR"]] = "LINEAR",
                       min_filter: Optional[
                           Literal["NEAREST", "LINEAR", "LINEAR_MIPMAP_LINEAR"]] = "LINEAR_MIPMAP_LINEAR",
                       wrap_s: Optional[SamplerMode] = "REPEAT",
                       wrap_t: Optional[SamplerMode] = "REPEAT") -> Sampler:
        """Add a Sampler object to the session. Will use a custom delegate if applicable.

        Args:
            name (str, optional): name of the sampler
            mag_filter (str, optional): magnification filter
            min_filter (str, optional): minification filter
            wrap_s (str, optional): wrap mode for s coordinate
            wrap_t (str, optional): wrap mode for t coordinate

        Returns:
            Sampler: sampler delegate that was created
        """
        return self.create_component(Sampler, name=name, mag_filter=mag_filter, min_filter=min_filter,
                                     wrap_s=wrap_s, wrap_t=wrap_t)

    def create_light(self, name: Optional[str] = None,
                     color: Optional[RGB] = (1.0, 1.0, 1.0),
                     intensity: Optional[float] = 1.0,
                     point: PointLight = None,
                     spot: SpotLight = None,
                     directional: DirectionalLight = None) -> Light:
        """Add a Light object to the session. Will use a custom delegate if applicable.

        Args:
            name (str, optional): name of the light
            color (RGB, optional): color of the light
            intensity (float, optional): intensity of the light on scale from 0-1
            point (PointLight, optional): point light information
            spot (SpotLight, optional): spot light information
            directional (DirectionalLight, optional): directional light information

        Returns:
            Light: light delegate that was created
        """
        return self.create_component(Light, name=name, color=color, intensity=intensity,
                                     point=point, spot=spot, directional=directional)

    def create_geometry(self, patches: list[GeometryPatch], name: Optional[str] = None) -> Geometry:
        """Add a Geometry object to the session. Will use a custom delegate if applicable.

        Args:
            patches (list[GeometryPatch]): list of geometry patches
            name (str, optional): name of the geometry

        Returns:
            Geometry: geometry delegate that was created
        """
        return self.create_component(Geometry, name=name, patches=patches)

    def create_table(self, name: Optional[str] = None,
                     meta: Optional[str] = None,
                     methods_list: Optional[list[MethodID]] = None,
                     signals_list: Optional[list[SignalID]] = None) -> Table:
        """Add a Table object to the session. Will use a custom delegate if applicable.

        Args:
            name (str, optional): name of the table
            meta (str, optional): meta description for the table
            methods_list (list[MethodID], optional): list of methods for the table
            signals_list (list[SignalID], optional): list of signals for the table

        Returns:
            Table: table delegate that was created
        """
        return self.create_component(Table, name=name, meta=meta, methods_list=methods_list, signals_list=signals_list)


# Helpers for ordering messages
def top_sort_recurse(id, refs, visited, components, stack):
    """Helper for order_components to recurse"""

    visited[id] = True
    if id in refs:
        for ref in refs[id]:
            if not visited[ref]:
                top_sort_recurse(ref, refs, visited, components, stack)

    stack.append(components[id])


def order_components(components: dict[ID, Delegate],
                     refs: dict[ID, list[ID]]):
    """Helper for creating topological sort of components"""

    visited = {key: False for key in components}
    stack = []

    for id in components:
        if not visited[id]:
            top_sort_recurse(id, refs, visited, components, stack)

    return stack[::-1]
