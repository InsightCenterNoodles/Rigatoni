from queue import Queue
from types import NoneType
from typing import Type, Union
from numpy import sign
from pydantic import BaseModel

import websockets

from . import noodle_objects as nooobs
from cbor2 import dumps


class Server(object):
    """NOODLES Server
    
    Attributes;
        clients (set): clients connections
        reference_graph (dict)
        ids (dict): 
            map object type to slot tracking info (next_slot, on_deck)
    """

    def __init__(self, methods, hardcoded_state, delegates):
        self.clients = set()
        self.custom_delegates = delegates
        self.delegates = {}
        self.ids = {}
        self.objects = {}
        self.components = [
            nooobs.Method,
            nooobs.Signal,
            nooobs.Table,
            nooobs.Plot,
            nooobs.Entity,
            nooobs.Material,
            nooobs.Geometry,
            nooobs.Geometry,
            nooobs.Image,
            nooobs.Texture,
            nooobs.Sampler,
            nooobs.Buffer,
            nooobs.BufferView
        ]
        self.message_map = {
            ("create", nooobs.Method): 0,
            ("delete", nooobs.Method): 1,
            ("create", nooobs.Signal): 2,
            ("delete", nooobs.Signal): 3,
            ("create", nooobs.Entity): 4,
            ("update", nooobs.Entity): 5,
            ("delete", nooobs.Entity): 6,
            ("create", nooobs.Plot): 7,
            ("update", nooobs.Plot): 8,
            ("delete", nooobs.Plot): 9,
            ("create", nooobs.Buffer): 10,
            ("delete", nooobs.Buffer): 11,
            ("create", nooobs.BufferView): 12,
            ("delete", nooobs.BufferView): 13,
            ("create", nooobs.Material): 14,
            ("update", nooobs.Material): 15,
            ("delete", nooobs.Material): 16,
            ("create", nooobs.Image): 17,
            ("delete", nooobs.Image): 18,
            ("create", nooobs.Texture): 19,
            ("delete", nooobs.Texture): 20,
            ("create", nooobs.Sampler): 21,
            ("delete", nooobs.Sampler): 22,
            ("create", nooobs.Light): 23,
            ("update", nooobs.Light): 24,
            ("delete", nooobs.Light): 25,
            ("create", nooobs.Geometry): 26,
            ("delete", nooobs.Geometry): 27,
            ("create", nooobs.Table): 28,
            ("update", nooobs.Table): 29,
            ("delete", nooobs.Table): 30,
            ("update", NoneType): 31,
            ("reset", NoneType): 32,
            ("invoke", nooobs.Invoke): 33,
            ("reply", nooobs.Reply): 34,
            ("initialized", NoneType): 35
        }

        # Set up user defined methods
        for name, method in methods.items():
            injected = nooobs.InjectedMethod(self, method)
            setattr(self, name, injected)

        # Initialize objects / Id's to use component type as key
        for component in self.components:
            self.objects[component] = {}
            self.delegates[component] = {}
            self.ids[component] = nooobs.SlotTracker()

        # Set up hardcoded state for initial testing
        for key, value in hardcoded_state.items():
            self.objects[key] = value


    def prepare_message(self, action: str, object: Union[nooobs.Component, nooobs.Model]=None, delta: list[str] = None):
        """Given object and action, get id and message contents as dict
        
        Not sure how I feel about this rn, analogous to handle in client but kinda messy here
        definitely revisit

        Args:
            object: Component, Reply, or Invoke
        """

        # Get ID for message
        id = self.message_map[(action, type(object))]

        # Get message contents
        contents = {}
        if action in {"create", "invoke", "reply"}:
            contents = object.dict(exclude_none=True)
        elif action == "update":

            # Document case
            if object == None:
                contents["methods_list"] = self.objects[nooobs.Method].keys()
                contents["signals_list"] = self.objects[nooobs.Signal].keys()
            # Normal update
            else:
                contents = object.dict(include=delta)

        elif action == "delete":
            contents["id"] = object.id

        elif action == "initialized" or action == "reset":
            pass

        return id, contents


    def broadcast(self, message: list):
        """Broadcast message to all connected clients"""
        
        print(f"Broadcasting Message: {message}")
        encoded = dumps(message)
        websockets.broadcast(self.clients, encoded)


    def handle_intro(self):
        """Formulate response for new client"""

        # Send create message for every object in state
        message = []
        for specifier, object_map, in self.objects.items():
            for id, object in object_map.items():
                id, content = self.prepare_message("create", object)
                message.extend([id, content])
        
        # Finish with initialization message
        message.extend(self.prepare_message("initialized"))    
        return message


    def handle_invoke(self, message: dict):
        """Takes message and formulates response for clients"""

        reply_obj = nooobs.Reply(invoke_id="-1")
        try:
            self.invoke_method(message, reply_obj)
        except nooobs.MethodException as e:
            reply_obj.method_exception = e       
        except Exception as e:
            print(f"\033[91mServerside Error: {e}\033[0m")
            reply_obj.method_exception = nooobs.MethodException(-32603, "Internal Error")
            
        return self.prepare_message("reply", reply_obj)


    def invoke_method(self, message: dict, reply: nooobs.Reply):
        
        # Parse message
        try:
            method_id = nooobs.IDGroup(*message["method"])
            context = message.get("context")
            invoke_id = message["invoke_id"]
            args: list = message["args"]
            reply.invoke_id = invoke_id
        except:
            raise nooobs.MethodException(-32700, "Parse Error")

        # Locate method
        try:
            method_name = self.objects[nooobs.Method][method_id].name                
            method = getattr(self, method_name)
        except:
            raise nooobs.MethodException(-32601, "Method Not Found")
        
        # Invoke
        reply.result = method(context, *args)


    # Interface methods to build server methods ================================
    def create_component(self, type: Type, **kwargs) -> nooobs.Component:
        """update state and clients with new object"""

        id = self.get_id(type)
        try:
            new_component = type(id=id, **kwargs)
        except:
            raise Exception(f"Args: {kwargs}, invalid for initializing a {type}")

        # Overhaul to create object in it as well
        self.objects[type][new_component.id] = new_component

        message = self.prepare_message("create", new_component)
        self.broadcast(message)

        # Return delegate instance if applicable
        if type in self.custom_delegates:
            delegate = self.custom_delegates[type](self, new_component)
            self.delegates[type][id] = delegate 
            return delegate
        else:
            return new_component


    def delete_component(self, obj: nooobs.Component):
        """Delete object in state and update clients"""
        
        # Update ID's available
        self.ids[type(obj)].on_deck.put(obj.id)
        
        # Update State - Component class takes care of broadcast
        del self.objects[type(obj)][obj.id]

    
    def update_component(self, obj: nooobs.Component):
        """Update object in stae and update clients"""

        # Update state
        state_obj = self.objects[type(obj)][obj.id]
        delta = []
        for field, val in obj.__fields__.items():
            if val != getattr(state_obj, field):
                setattr(state_obj, field, val)
                delta.append(field)

        # Broadcast update with only changed values
        message = self.prepare_message("update", obj, delta)
        self.broadcast(message)


    def invoke_signal(self, signal, on_component, signal_data):
        """Send signal to target component"""

        # Get context from on_component
        context = None
        if isinstance(on_component, nooobs.Entity):
            context = nooobs.InvokeIDType(entity=on_component.id)
        elif isinstance(on_component, nooobs.Table):
            context = nooobs.InvokeIDType(table=on_component.id)
        elif isinstance(on_component, nooobs.Plot):
            context = nooobs.InvokeIDType(plot=on_component.id)

        # Create invoke object and broadcast message
        invoke = nooobs.Invoke(id=signal.id, context=context, signal_data=signal_data)
        message = self.prepare_message("invoke", invoke)
        self.broadcast(message)
        

    def get_id(self, type) -> nooobs.IDGroup:
        """Get ID with next open slot
        
        Check for open slots then take closest available slot
        """

        slot_info = self.ids[type]
        if slot_info.on_deck.empty():
            id = nooobs.IDGroup(slot_info.next_slot, 0)
            slot_info.next_slot += 1
            return id
        else:
            return slot_info.on_deck.get()             