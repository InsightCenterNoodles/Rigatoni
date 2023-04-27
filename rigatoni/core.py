"""Module with core implementation of Server Object"""

from __future__ import annotations
from types import NoneType
from typing import TYPE_CHECKING, Type, TypeVar
import asyncio
import functools
import logging

if TYPE_CHECKING:
    from . import delegates

import websockets
from cbor2 import loads, dumps
import json

from .noodle_objects import *


# To allow for more flexible type annotation especially in create component
T = TypeVar("T", bound=Component)


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
            document's current state, contains all components with component ID 
            as the key
        references (dict):
            maps component ID to all the component ID's that reference it
        delete_queue (set):
            components that are referenced but have been requested to be deleted
        message_map (dict):
            maps action and type to message ID
    """

    def __init__(self, port: int, starting_state: list[StartingComponent],
                 delegate_map: dict[Type[Component], Type[delegates.Delegate]] = None):
        """Constructor
        
        Args:
            port (int):
                port to run server on
            starting_state (list[StartingComponent]):
                list of objects containing the info to create components on initialization
            delegate_map (dict):
                maps noodles component type to instance of delegate class
        Raises:
            Exception: Invalid Arguments or Method Not Specified when filling in starting state
        """

        self.port = port
        self.clients = set()
        self.custom_delegates = delegate_map if delegate_map else {}
        self.delegates = {}
        self.ids = {}
        self.components = {}
        self.references = {}
        self.delete_queue = set()
        self.shutdown_event = asyncio.Event()

        self.message_map = {
            ("create", Method): 0,
            ("delete", Method): 1,
            ("create", Signal): 2,
            ("delete", Signal): 3,
            ("create", Entity): 4,
            ("update", Entity): 5,
            ("delete", Entity): 6,
            ("create", Plot): 7,
            ("update", Plot): 8,
            ("delete", Plot): 9,
            ("create", Buffer): 10,
            ("delete", Buffer): 11,
            ("create", BufferView): 12,
            ("delete", BufferView): 13,
            ("create", Material): 14,
            ("update", Material): 15,
            ("delete", Material): 16,
            ("create", Image): 17,
            ("delete", Image): 18,
            ("create", Texture): 19,
            ("delete", Texture): 20,
            ("create", Sampler): 21,
            ("delete", Sampler): 22,
            ("create", Light): 23,
            ("update", Light): 24,
            ("delete", Light): 25,
            ("create", Geometry): 26,
            ("delete", Geometry): 27,
            ("create", Table): 28,
            ("update", Table): 29,
            ("delete", Table): 30,
            ("update", NoneType): 31,
            ("reset", NoneType): 32,
            ("invoke", Invoke): 33,
            ("reply", Reply): 34,
            ("initialized", NoneType): 35
        }

        # Set up starting state
        for starting_component in starting_state:
            comp_type = starting_component.type
            comp_method = starting_component.method
            try:
                comp = self.create_component(comp_type, **starting_component.component_attrs)
            except:
                raise Exception(f"Invalid arguments to create {comp_type}")

            if comp_type == Method:
                if comp_method:
                    injected = InjectedMethod(self, comp_method)
                    setattr(self, comp.name, injected)
                else:
                    raise Exception("Method not specified for starting method")
        logging.debug(f"Server initialized with objects: {self.components}")

    def __enter__(self):
        """Enter context manager"""
        return self.run(yielding=True)

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context manager"""
        self.shutdown()

    def run(self, yielding=False):
        """Run the server"""
        return asyncio.run(self.start_server(yielding=yielding))

    async def start_server(self, yielding=False):
        """Run the server and listen for connections"""
        # Create partial to pass server to handler
        handler = functools.partial(self.handle_client)

        logging.info("Starting up Server...")
        async with websockets.serve(handler, "", self.port):
            if yielding:
                return self
            while not self.shutdown_event.is_set():
                await asyncio.sleep(.1)

    def shutdown(self):
        """Shutdown the server"""
        logging.info("Shutting down server...")
        self.shutdown_event.set()

    @staticmethod
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

        # Update state
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

    def get_ids_by_type(self, component: Type[Component]) -> list:
        """Helper to get all ids for certain component type
        
        Args:
            component (type): type of component to get ID's for
        """

        return [key for key, val in self.components.items() if isinstance(val, component)]

    def get_component_id(self, kind: Type[Component], name: str):
        """Helper to get a component with a type and name"""

        for comp_id, comp in self.components.items():
            if isinstance(comp, kind) and comp.name == name:
                return comp_id
        raise Exception("No Component Found")

    def get_component(self, comp_id: ID):
        """Getter for users to access components in state"""

        try:
            return self.components[comp_id].copy(deep=True)
        except ValueError:
            raise Exception("No Component Found")

    def get_message_contents(self, action: str, noodle_object: NoodleObject, delta: set[str]):
        """Helper to handle construction of message dict
        
        Args:
            action (str): action taken with message
            noodle_object (NoodleObject): Component, Reply, or Invoke object
            delta (set): field names to be included in update
        """

        contents = {}
        if action in {"create", "invoke", "reply"}:
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

        message_id = self.message_map[(action, type(noodle_object))]
        contents = self.get_message_contents(action, noodle_object, delta)

        return message_id, contents

    def broadcast(self, message: tuple):
        """Broadcast message to all connected clients
        
        Args:
            message [tuple]: fully constructed message in form (tag/id, contents)
        """

        logging.debug(f"Broadcasting Message: ID's {message[::2]}")
        json_message = json.dumps(message, default=default_json_encoder)
        with open("sample_messages.json", "a") as outfile:
            outfile.write(json_message)
        encoded = dumps(message)
        websockets.broadcast(self.clients, encoded)

    def handle_intro(self):
        """Formulate response for new client"""

        # Add create message for every object in state
        message = []
        ordered_components = order_components(self.components, self.references)
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
            raise Exception(MethodException(code=-32700, message="Parse Error"))

        # Locate method
        try:
            method_name = self.components[method_id].name
            method = getattr(self, method_name)
        except Exception:
            raise Exception(MethodException(code=-32601, message="Method Not Found"))

        # Invoke
        reply.result = method(context, *args)

    def update_references(self, comp: Component, current: NoodleObject, removing=False):
        """Update in-degree for all objects referenced by this one

        Recursively updates references for all components under a parent one. Here,
        the current object changes through the recursion while comp keeps track of 
        the parent 
        
        Args:
            comp (Component): parent component with new references to be tracked
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
            elif val and isinstance(val, list):

                # Objects
                if isinstance(val[0], NoodleObject):
                    for obj in val:
                        self.update_references(comp, obj, removing)

                # ID's
                elif isinstance(val[0], ID):
                    for id in val:
                        if removing:
                            self.references[id].remove(comp.id)
                        else:
                            self.references.setdefault(id, set()).add(comp.id)

    def get_id(self, comp_type: Type[Component]) -> IDGroup:
        """Get next open ID
        
        Check for open slots then take the closest available slot

        Args:
            comp_type (Component Type): type for desired ID
        """

        if comp_type in self.ids:
            slot_info = self.ids[comp_type]
        else:
            slot_info = SlotTracker()
            self.ids[comp_type] = slot_info

        if slot_info.on_deck.empty():
            id_type = id_map[comp_type]
            id = id_type(slot=slot_info.next_slot, gen=0)
            slot_info.next_slot += 1
            return id
        else:
            return slot_info.on_deck.get()

    # Interface methods to build server methods ===============================================

    def create_component(self, comp_type: Type[T], **kwargs) -> Union[T, delegates.Delegate]:
        """Officially create new component in state
        
        This method updates state, updates references, and broadcasts msg to clients.
        It also handles the acquisition of a valid ID
        
        Args:
            comp_type (Component Type): type of component to be created
            **kwargs: the user should specify the attributes of the component using 
                keyword arguments. Refer to the noodle objects to see which attributes
                are required and optional. Any deviation from the spec will raise a 
                validation exception. Note that since this method handles the ID, it 
                should not be specified as one of the keyword arguments.
        """

        # Get ID and try to create component from args
        comp_id = self.get_id(comp_type)
        try:
            new_component = comp_type(id=comp_id, **kwargs)
        except:
            raise Exception(f"Args: {kwargs}, invalid for initializing a {comp_type}")

        # Update state
        self.components[comp_id] = new_component

        # Update references for each component referenced by this one
        self.update_references(new_component, new_component)

        # Create message and broadcast
        message = self.prepare_message("create", new_component)
        self.broadcast(message)

        # Return component or delegate instance if applicable
        if self.custom_delegates and comp_type in self.custom_delegates:
            delegate = self.custom_delegates[comp_type](self, new_component)
            self.delegates[id] = delegate
            return delegate
        else:
            return new_component.copy(deep=True)

    def delete_component(self, obj: Union[Component, delegates.Delegate, ID]):
        """Delete object in state and update clients
        
        This method excepts a delegate, component, or component ID, and will attempt
        to delete the component as long as it is not referenced by any other component.
        If this component is still being used by another, it will be added to a queue so that
        it can be deleted later once that reference is no longer being used.

        Args:
            obj (Component, Delegate, or ID): component / delegate to be deleted
        """

        # Handle cases so can except different input types
        if type(obj) in self.custom_delegates.values():
            id = obj.component.id
            del self.delegates[id]
        elif isinstance(obj, Component):
            id = obj.id
        else:
            id = obj

        # Delete if no references, or else queue it up for later
        if not self.references.get(id):
            self.broadcast(self.prepare_message("delete", self.components[id]))
            del self.components[id]

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
                logging.warning(f"Couldn't delete {self.components[obj]}, "
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

    def update_component(self, obj: Component):
        """Update clients with changes to a component
        
        This method broadcasts changes to all clients including only fields
        specified in the set delta

        Args:
            obj (Component): component that has been updated, 
                should be a component with an update message
        """

        # Update references and find delta
        state_obj = self.components[obj.id]
        delta = self.find_delta(state_obj, obj)

        # Update State
        self.components[obj.id] = obj

        # Form message and broadcast
        try:
            message = self.prepare_message("update", obj, delta)
            self.broadcast(message)
        except:
            raise Exception("This obj can not be updated")

    def invoke_signal(self, signal: SignalID, on_component: Component, signal_data: list):
        """Send signal to target component
        
        Args:
            signal (ID): signal to be invoked
            on_component (Component): component to receive the signal
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


def order_components(components: dict[ID, Component],
                     refs: dict[ID, list[ID]]):
    """Helper for creating topological sort of components"""

    visited = {key: False for key in components}
    stack = []

    for id in components:
        if not visited[id]:
            top_sort_recurse(id, refs, visited, components, stack)

    return stack[::-1]
