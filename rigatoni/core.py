"""Module with core implementation of Server Object"""

from __future__ import annotations
from typing import Type, TypeVar, Literal
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
    """NOODLES Server
    
    Attributes;
        clients (set): client connections
        custom_delegates (dict): 
            maps noodle object to its delegate class, empty by default
        delegates (dict):
            maps component ID to its delegate instance
        ids (dict): 
            maps object type to slot tracking info (next_slot, on_deck)
        components (dict):
            document's current state, contains all components with component ID as the key
        references (dict):
            maps component ID to all the component ID's that reference it
        delete_queue (set):
            components that are referenced but have been requested to be deleted
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
            Exception: Invalid Arguments or Method Not Specified when filling in starting state
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
        self.json_output = json_output

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
            except TypeError:
                raise Exception(f"Invalid arguments to create {comp_type}")

            if comp_type == Method and comp_method:
                injected = InjectedMethod(self, comp_method)
                setattr(self, comp.name, injected)
            elif comp_type == Method and not comp_method:
                raise Exception("Method not specified for starting method")

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
        """Run the server"""
        return asyncio.run(self.start_server())

    async def start_server(self):
        """Run the server and listen for connections"""
        # Create partial to pass server to handler
        handler = functools.partial(self.handle_client)

        logging.info("Starting up Server...")
        async with websockets.serve(handler, "", self.port):
            self.ready.set()
            while not self.shutdown_event.is_set():
                await asyncio.sleep(.1)

    def shutdown(self):
        """Shutdown the server"""
        logging.info("Shutting down server...")
        self.shutdown_event.set()

    def log_json(self, message: list):
        json_message = json.dumps(message, default=default_json_encoder)
        with open(self.json_output, "a") as outfile:
            outfile.write(json_message)

    async def send(self, websocket, message: list):
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
            self.log_json(message)

        # Log message and send
        logging.debug(f"Sending Message: ID's {message[::2]}")
        await websocket.send(dumps(message))

    async def handle_client(self, websocket):
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

        init_message = self.handle_intro()
        await self.send(websocket, init_message)

        # Listen for method invocation and keep all clients informed
        async for message in websocket:
            # Decode and log raw message
            message = loads(message)
            logging.debug(f"Message from client: {message}")

            # Handle the method invocation
            reply = self.handle_invoke(message[1])

            # Send method reply to client
            await self.send(websocket, list(reply))

        # Remove client if disconnected
        logging.debug(f"Client 'client_name' disconnected")
        self.clients.remove(websocket)

    def get_ids_by_type(self, component: Type[Delegate]) -> list:
        """Helper to get all ids for certain component type
        
        Args:
            component (type): type of component to get ID's for
        """

        return [key for key, val in self.state.items() if isinstance(val, component)]

    def get_delegate_id(self, name: str):
        """Helper to get a component with a type and name"""

        for delegate in self.state.values():
            if delegate.name == name:
                return delegate.id
        raise Exception("No Component Found")

    def get_delegate(self, identifier: Union[ID, str, Dict[str, ID]]):
        """Getter for users to access components in state

        Can be called with an ID, name, or context of the delegate
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
        """Helper to get a component by context"""

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

    def get_message_contents(self, action: str, noodle_object: NoodleObject, delta: set[str]):
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

        elif action == "invoke" or action == "reply":
            contents = noodle_object.dict(exclude_none=True)

        elif action == "update":
            if not noodle_object:  # Document case
                contents["methods_list"] = self.get_ids_by_type(Method)
                contents["signals_list"] = self.get_ids_by_type(Signal)
            else:  # Normal update, include id, and any field in delta
                delta = {} if not delta else delta
                delta.add("id")
                contents = noodle_object.dict(exclude_none=True, include=delta)

        elif action == "delete":
            try:
                contents["id"] = noodle_object.id
            except AttributeError:
                raise Exception(f"Cannot delete a {noodle_object}")

        return contents

    def prepare_message(self, action: str, noodle_object: NoodleObject = None, delta: set[str] = None):
        """Given object and action, get id and message contents as dict

        Args:
            action (str): action taken with message
            noodle_object (NoodleObject): Component, Reply, or Invoke object
            delta (set): field names to be included in update
        """

        delegate_type = None if not isinstance(noodle_object, Delegate) else type(noodle_object.id)
        key = (action, delegate_type)
        message_id = self.message_map[key]
        contents = self.get_message_contents(action, noodle_object, delta)

        return message_id, contents

    def broadcast(self, message: list):
        """Broadcast message to all connected clients
        
        Args:
            message [tuple]: fully constructed message in form (tag/id, contents)
        """

        # Log message in json file if applicable
        if self.json_output:
            self.log_json(message)

        logging.debug(f"Broadcasting Message: ID's {message[::2]}")
        encoded = dumps(message)
        websockets.broadcast(self.clients, encoded)

    def handle_intro(self):
        """Formulate response for new client"""

        # Add create message for every object in state
        message = []
        ordered_components = order_components(self.state, self.references)
        for component in ordered_components:
            msg_id, content = self.prepare_message("create", component)
            message.extend([msg_id, content])

        # Add document update
        message.extend(self.prepare_message("update", None))

        # Finish with initialization message
        message.extend(self.prepare_message("initialized"))
        return message

    def handle_invoke(self, message: dict):
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
            self.invoke_method(message, reply_obj)

        except Exception as e:
            if type(e) is MethodException:
                reply_obj.method_exception = e
            else:
                logging.error(f"\033[91mServerside Error: {e}\033[0m")
                reply_obj.method_exception = MethodException(code=-32603, message="Internal Error")

        return self.prepare_message("reply", reply_obj)

    def invoke_method(self, message: dict, reply: Reply):
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

    def update_references(self, comp: Delegate, current: NoodleObject, removing=False):
        """Update in-degree for all objects referenced by this one

        Recursively updates references for all components under a parent one. Here,
        the current object changes through the recursion while comp keeps track of 
        the parent 
        
        Args:
            comp (Delegate): parent component with new references to be tracked
            current (NoodleObject): current object being examined
            removing (bool): flag so function can be used to both add and remove references
        """

        for key in current.__fields__.keys():
            val = getattr(current, key)

            # Found a reference
            if key != "id" and isinstance(val, ID):
                if removing:
                    self.references[val].remove(comp.id)
                else:
                    self.references.setdefault(val, set()).add(comp.id)

            # Found another object to recurse on
            elif isinstance(val, NoodleObject):
                self.update_references(comp, val, removing)

            # Found list of objects or id's to recurse on 
            elif val is not None and isinstance(val, list):

                # Objects
                if len(val) > 0 and isinstance(val[0], NoodleObject):
                    for obj in val:
                        self.update_references(comp, obj, removing)

                # ID's
                elif len(val) > 0 and isinstance(val[0], ID):
                    for id in val:
                        if removing:
                            self.references[id].remove(comp.id)
                        else:
                            self.references.setdefault(id, set()).add(comp.id)

    def get_id(self, delegate_type: Type[Delegate]) -> ID:
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
        more specific versions exist for each component type
        
        Args:
            comp_type (Component Type): type of component to be created
            **kwargs: the user should specify the attributes of the component using 
                keyword arguments. Refer to the noodle objects to see which attributes
                are required and optional. Any deviation from the spec will raise a 
                validation exception. Note that since this method handles the ID, it 
                should not be specified as one of the keyword arguments.
        """

        # Get ID and try to create delegate from args
        comp_type = self.custom_delegates.get(comp_type, comp_type)
        comp_id = self.get_id(comp_type)
        try:
            new_delegate = comp_type(server=self, id=comp_id, **kwargs)
        except Exception as e:
            raise Exception(f"Args: {kwargs}, invalid for initializing a {comp_type}: {e}")

        # Update state and keep track of initial version for changes / update messages
        self.state[comp_id] = new_delegate
        self.client_state[comp_id] = new_delegate

        # Update references for each component referenced by this one
        self.update_references(new_delegate, new_delegate)

        # Create message and broadcast
        message = self.prepare_message("create", new_delegate)
        self.broadcast(message)

        # Return component or delegate instance if applicable
        return new_delegate

    def delete_component(self, obj: Union[Delegate, ID]):
        """Delete object in state and update clients
        
        This method excepts a delegate, component, or component ID, and will attempt
        to delete the component as long as it is not referenced by any other component.
        If this component is still being used by another, it will be added to a queue so that
        it can be deleted later once that reference is no longer being used.

        Args:
            obj (Component, Delegate, or ID): component / delegate to be deleted
        """

        # Handle cases so can except different input types
        if isinstance(obj, Delegate):
            id = obj.id
        else:
            id = obj

        # Delete if no references, or else queue it up for later
        if not self.references.get(id):
            self.broadcast(self.prepare_message("delete", self.state[id]))
            del self.state[id]
            del self.client_state[id]

            # Clean out references from this object
            for refs in self.references.values():
                while id in refs:
                    refs.remove(id)

            # Check if anything in the queue is now clear to be deleted
            for comp_id in list(self.delete_queue):
                if not self.references.get(comp_id):
                    self.delete_queue.remove(comp_id)
                    self.delete_component(comp_id)

        else:
            if isinstance(obj, ID):
                logging.warning(f"Couldn't delete {self.state[obj]}, "
                                f"referenced by {self.references[id]}, added to queue")
            else:
                logging.warning(f"Couldn't delete {obj}, referenced by {self.references[id]}, added to queue")
            self.delete_queue.add(id)

    def find_delta(self, state, edited):
        """Helper to find differences between two objects
        
        Also checks to find recursive cases and cases where references
        should be updated, Does this get recursive deltas tho? should it?
        """

        delta = set()
        for field_name, value in edited:
            state_val = getattr(state, field_name)
            if value != state_val:
                delta.add(field_name)
                if isinstance(value, NoodleObject):
                    self.update_references(state, state_val, removing=True)
                    self.update_references(edited, value)

        return delta

    def update_component(self, state_obj: Delegate):
        """Update clients with changes to a component
        
        This method broadcasts changes to all clients including only fields
        specified in the set delta

        Args:
            state_obj (Delegate): component that has been updated,
                should be a component with an update message
        """

        # Update references and find delta
        delta = self.find_delta(self.client_state[state_obj.id], state_obj)

        # Update tracking state
        self.client_state[state_obj.id] = state_obj

        # Form message and broadcast
        try:
            message = self.prepare_message("update", state_obj, delta)
            self.broadcast(message)
        except Exception as e:
            raise Exception(f"This obj can not be updated: {e}")

    def invoke_signal(self, signal: SignalID, on_component: Delegate, signal_data: list):
        """Send signal to target component
        
        Args:
            signal (ID): signal to be invoked
            on_component (Delegate): component to receive the signal
            signal_data (dict): 
        Takes Signal ID, on_component, and the data
        """

        # Get context from on_component
        if isinstance(on_component, Entity):
            context = InvokeIDType(entity=on_component.id)
        elif isinstance(on_component, Table):
            context = InvokeIDType(table=on_component.id)
        elif isinstance(on_component, Plot):
            context = InvokeIDType(plot=on_component.id)
        else:
            raise Exception(f"Invalid on_component type: {type(on_component)}")

        # Create invoke object and broadcast message
        invoke = Invoke(id=signal, context=context, signal_data=signal_data)
        message = self.prepare_message("invoke", invoke)
        self.broadcast(message)

    def create_method(self, name: str,
                      arg_doc: list[MethodArg],
                      doc: Optional[str] = None,
                      return_doc: Optional[str] = None) -> Method:
        return self.create_component(Method, name=name, doc=doc, return_doc=return_doc, arg_doc=arg_doc)

    def create_signal(self, name: str,
                      doc: Optional[str] = None,
                      arg_doc: list[MethodArg] = None) -> Signal:
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

        return self.create_component(Plot, name=name, table=table, simple_plot=simple_plot, url_plot=url_plot,
                                     methods_list=methods_list, signals_list=signals_list)

    def create_buffer(self, name: Optional[str] = None,
                      size: int = None,
                      inline_bytes: bytes = None,
                      uri_bytes: str = None) -> Buffer:
        return self.create_component(Buffer, name=name, size=size, inline_bytes=inline_bytes, uri_bytes=uri_bytes)

    def create_bufferview(self,
                          source_buffer: BufferID,
                          offset: int,
                          length: int,
                          name: Optional[str] = None,
                          type: Literal["UNK", "GEOMETRY", "IMAGE"] = "UNK") -> BufferView:
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
        return self.create_component(Material, name=name, pbr_info=pbr_info, normal_texture=normal_texture,
                                     occlusion_texture=occlusion_texture,
                                     occlusion_texture_factor=occlusion_texture_factor,
                                     emissive_texture=emissive_texture, emissive_factor=emissive_factor,
                                     use_alpha=use_alpha, alpha_cutoff=alpha_cutoff, double_sided=double_sided)

    def create_image(self, name: Optional[str] = None,
                     buffer_source: BufferID = None,
                     uri_source: str = None) -> Image:
        return self.create_component(Image, name=name, buffer_source=buffer_source, uri_source=uri_source)

    def create_texture(self, image: ImageID,
                       name: Optional[str] = None,
                       sampler: Optional[SamplerID] = None) -> Texture:
        return self.create_component(Texture, name=name, image=image, sampler=sampler)

    def create_sampler(self, name: Optional[str] = None,
                       mag_filter: Optional[Literal["NEAREST", "LINEAR"]] = "LINEAR",
                       min_filter: Optional[
                           Literal["NEAREST", "LINEAR", "LINEAR_MIPMAP_LINEAR"]] = "LINEAR_MIPMAP_LINEAR",
                       wrap_s: Optional[SamplerMode] = "REPEAT",
                       wrap_t: Optional[SamplerMode] = "REPEAT") -> Sampler:
        return self.create_component(Sampler, name=name, mag_filter=mag_filter, min_filter=min_filter,
                                     wrap_s=wrap_s, wrap_t=wrap_t)

    def create_light(self, name: Optional[str] = None,
                     color: Optional[RGB] = (1.0, 1.0, 1.0),
                     intensity: Optional[float] = 1.0,
                     point: PointLight = None,
                     spot: SpotLight = None,
                     directional: DirectionalLight = None) -> Light:
        return self.create_component(Light, name=name, color=color, intensity=intensity,
                                     point=point, spot=spot, directional=directional)

    def create_geometry(self, patches: list[GeometryPatch], name: Optional[str] = None) -> Geometry:
        return self.create_component(Geometry, name=name, patches=patches)

    def create_table(self, name: Optional[str] = None,
                     meta: Optional[str] = None,
                     methods_list: Optional[list[MethodID]] = None,
                     signals_list: Optional[list[SignalID]] = None) -> Table:
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
