from collections import namedtuple
from dataclasses import asdict, fields, is_dataclass
from queue import Queue
from types import NoneType

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

    def __init__(self, methods, hardcoded_state):
        self.clients = set()
        self.reference_graph = {}
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
            ("invoke", nooobs.Signal): 33,
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
            self.ids[component] = nooobs.SlotTracker()

        # Set up hardcoded state for initial testing
        for key, value in hardcoded_state.items():
            self.objects[key] = value


    def prepare_message(self, action: str, object=None, delta: list[str] = None):
        """Given object and action, get id and message contents as dict
        
        Not sure how I feel about this rn, analogous to handle in client but kinda messy here
        definitely revisit
        """

        # Get ID for message
        id = self.message_map[(action, type(object))]

        # Get message contents
        contents = {}
        if action in {"create", "invoke"}:
            contents = msg_from_obj(object)
        elif action == "update":

            # Document case
            if object == None:
                contents["methods_list"] = self.objects[nooobs.Method].keys()
                contents["signals_list"] = self.objects[nooobs.Signal].keys()
            # Normal update
            else:
                msg_from_obj(object, delta)

        elif action == "delete":
            contents["id"] = object.id

        elif action == "reply":
            contents = msg_from_obj(object)

        elif action == "initialized" or action == "reset":
            pass


        return id, contents


    def broadcast(self, message: list):
        """Broadcast message to all connected clients"""
        
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

        reply_obj = nooobs.Reply("")
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
            print(f"Handling message w/ method: {method_id}, context: {context}, args: {args}")
        except:
            raise nooobs.MethodException(-32700, "Parse Error")

        # Locate method
        try:
            method_name = self.objects[nooobs.Method][method_id].name                
            method = getattr(self, method_name)
        except:
            raise nooobs.MethodException(-32601, "Method Not Found")
        
        # Invoke
        reply.result = method(*args)


    # Interface methods to build server methods ===============================
    def create_object(self, obj):
        """update state and clients with new object"""

        self.objects[type(obj)][obj.id] = obj
        message = self.prepare_message("create", obj)
        self.broadcast(message)


    def delete_object(self, obj):
        """Delete object in state and update clients"""
        
        # Update Reference Map (eventually)...
        

        # Update ID's available
        new_id = nooobs.IDGroup(obj.id.slot, obj.id.gen + 1)
        self.ids[type(obj)].on_deck.put(new_id)
        
        # Update State
        del self.objects[type(obj)][obj.id]

        # Inform Delegates
        message = self.prepare_message("delete", obj)
        self.broadcast(message)

    
    def update_object(self, obj):
        """Update object in stae and update clients"""

        # Update state
        state_obj = self.objects[type(obj)][obj.id]
        delta = []
        for field in fields(obj):
            key = field.name
            val = getattr(obj, key)
            if val != state_obj[key]:
                state_obj.key = val
                delta.append(key)

        # Broadcast update with only changed values
        message = self.prepare_message("update", obj, delta)
        self.broadcast(message)


    def invoke_signal(self, signal, on_component, signal_data):
        """Send signal to target component"""

        id = signal.id

        context = None
        if isinstance(on_component, nooobs.Entity):
            context = nooobs.InvokeIDType(entity=on_component.id)
        elif isinstance(on_component, nooobs.Table):
            context = nooobs.InvokeIDType(table=on_component.id)
        elif isinstance(on_component, nooobs.Plot):
            context = nooobs.InvokeIDType(plot=on_component.id)

        invoke = nooobs.Invoke(id, signal_data, context)
        message = self.prepare_message("invoke", invoke)
        self.broadcast(message)
        

    def get_id(self, type) -> nooobs.IDGroup:
        """Get ID with next open slot"""

        slot_info = self.ids[type]
        if slot_info.on_deck.empty():
            id = nooobs.IDGroup(slot_info.next_slot, 0)
            slot_info.next_slot += 1
            return id
        else:
            return slot_info.on_deck.get()
        


def msg_from_obj(obj, delta: list[str]=None):
    """Return dict of all objects attributes that are not None"""

    if not delta: delta = [f.name for f in fields(obj)]

    contents = {}
    for field in fields(obj):
        val = getattr(obj, field.name)
        
        if val != None and field.name in delta:
            if is_dataclass(val):
                val = msg_from_obj(val)
            contents[field.name] = val
    return contents