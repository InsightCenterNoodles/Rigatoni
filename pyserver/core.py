from __future__ import annotations
from queue import Queue
from types import NoneType
from typing import TYPE_CHECKING, Union
if TYPE_CHECKING:
    from . import interface

from matplotlib.style import available
from numpy import sign
import websockets
from cbor2 import dumps

from . import noodle_objects as nooobs


class Server(object):
    """NOODLES Server
    
    Attributes;
        clients (set): clients connections
        reference_graph (dict)
        ids (dict): 
            map object type to slot tracking info (next_slot, on_deck)
    """

    def __init__(self, methods: dict, hardcoded_state: dict, delegates: dict):
        self.clients = set()
        self.custom_delegates = delegates
        self.delegates = {}
        self.ids = {}
        self.components = {}
        self.references = {}
        self.delete_queue = set()
        
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

        # Set up hardcoded state for initial testing
        for component in hardcoded_state:
            self.components[component.id] = component

    # Gettters
    def get_ids_by_type(self, ctype) -> list:
        """Helper to get all ids for certain component type"""

        return [key for key, val in self.components.items() if isinstance(val, ctype)]


    def get_component_id(self, type, name: str):
        """Helper to get a component with a type and name"""

        for id, comp in self.components.items():
            if isinstance(comp, type) and hasattr(comp, "name") and comp.name == name:
                return id
        raise Exception("No component found exception")


    def prepare_message(self, action: str, object: Union[nooobs.Component, nooobs.NoodleObject]=None, delta: list[str] = None):
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
                contents["methods_list"] = self.get_ids_by_type(nooobs.Method)
                contents["signals_list"] = self.get_ids_by_type(nooobs.Signal)
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
        for object in self.components.values():
            msg_id, content = self.prepare_message("create", object)
            message.extend([msg_id, content])
        
        # Finish with initialization message
        message.extend(self.prepare_message("initialized"))    
        return message


    def handle_invoke(self, message: dict):
        """Takes message and formulates response for clients"""

        reply_obj = nooobs.Reply(invoke_id="-1")
        try:
            self.invoke_method(message, reply_obj)
        except Exception as e:
            if type(e) is nooobs.MethodException:
                reply_obj.method_exception = e
            else:
                print(f"\033[91mServerside Error: {e}\033[0m")
                reply_obj.method_exception = nooobs.MethodException(code=-32603, message="Internal Error")
            
        return self.prepare_message("reply", reply_obj)


    def invoke_method(self, message: dict, reply: nooobs.Reply):
        
        # Parse message
        try:
            method_id = nooobs.MethodID(*message["method"])
            context = message.get("context")
            invoke_id = message["invoke_id"]
            args: list = message["args"]
            reply.invoke_id = invoke_id
        except:
            raise Exception(nooobs.MethodException(code=-32700, message="Parse Error"))

        # Locate method
        try:
            method_name = self.components[method_id].name                
            method = getattr(self, method_name)
        except:
            raise Exception(nooobs.MethodException(code=-32601, message="Method Not Found"))
        
        # Invoke
        reply.result = method(context, *args)
    

    def update_references(self, comp: nooobs.Component, target: nooobs.NoodleObject):
        """Update indegree for all objects referenced by this one"""

        for key in target.__fields__.keys():
            val = getattr(target, key)

            # Found a reference
            if key != "id" and isinstance(val, nooobs.ID):
                self.references.setdefault(val, []).append(comp.id)

            # Found another object to recurse on
            elif isinstance(val, nooobs.NoodleObject):
                self.update_references(comp, val)

            # found list of objects to recurse on 
            elif isinstance(val, list) and isinstance(val[0], nooobs.NoodleObject):
                for obj in val:
                    self.update_references(comp, obj)
        

    # Interface methods to build server methods ================================
    def create_component(self, comp_type: type, **kwargs) -> nooobs.Component:
        """update state and clients with new object"""

        # Get ID and try to create component from args
        id = self.get_id(comp_type)
        try:
            new_component = comp_type(id=id, **kwargs)
        except:
            raise Exception(f"Args: {kwargs}, invalid for initializing a {comp_type}")

        # Update state
        self.components[id] = new_component

        # Update references for each component referenced by this one
        self.update_references(new_component, new_component)

        message = self.prepare_message("create", new_component)
        self.broadcast(message)

        # Return delegate instance if applicable
        if self.custom_delegates and comp_type in self.custom_delegates:
            delegate = self.custom_delegates[comp_type](self, new_component)
            self.delegates[id] = delegate 
            return delegate
        else:
            return new_component

    
    def delete_delegate(self, delegate):
        """Delete a delegate and its contents"""
        
        comp_id = delegate.component.id
        self.delete_component(comp_id)
        del self.delegates[comp_id.id]


    def delete_component(self, obj: Union[nooobs.Component, interface.Delegate, nooobs.ID]):
        """Delete object in state and update clients
        
        Update State - Component class takes care of ID's / broadcast

        obj should be a noodles component or delegate containing one
        """

        # Handle cases so can except different input types
        if type(obj) in self.custom_delegates.values():
            self.delete_delegate(obj)
        elif isinstance(obj, nooobs.Component):
            id = obj.id
        else:
            id = obj
            
        # Delete if no references, or else queue it up for later
        if not self.references.get(id):
            self.broadcast(self.prepare_message("delete", self.components[id]))
            del self.components[id]

            # Clean out references from this object
            for refs in self.references.values():
                while id in refs: refs.remove(id)
                    

            # Check if anything in the queue is now clear to be deleted
            for comp_id in self.delete_queue:
                if not self.references.get(comp_id):
                    self.delete_component(comp_id)

        else:
            print(f"Couldn't delete {obj}, referenced by {self.references[id]}, added to queue")
            self.delete_queue.add(id)

    
    def update_component(self, obj: nooobs.Component):
        """Update object in stae and update clients"""

        # Update state
        state_obj = self.components[obj.id]
        delta = []
        for field, val in obj.__fields__.items():
            if val != getattr(state_obj, field):
                setattr(state_obj, field, val)
                delta.append(field)

        # Broadcast update with only changed values
        message = self.prepare_message("update", obj, delta)
        self.broadcast(message)


    def invoke_signal(self, signal, on_component, signal_data):
        """Send signal to target component
        
        Takes Signal ID, on_component, and the data
        """

        # Get context from on_component
        context = None
        if isinstance(on_component, nooobs.Entity):
            context = nooobs.InvokeIDType(entity=on_component.id)
        elif isinstance(on_component, nooobs.Table):
            context = nooobs.InvokeIDType(table=on_component.id)
        elif isinstance(on_component, nooobs.Plot):
            context = nooobs.InvokeIDType(plot=on_component.id)

        # Create invoke object and broadcast message
        invoke = nooobs.Invoke(id=signal, context=context, signal_data=signal_data)
        message = self.prepare_message("invoke", invoke)
        self.broadcast(message)
        

    def get_id(self, comp_type) -> nooobs.IDGroup:
        """Get ID with next open slot
        
        Check for open slots then take closest available slot
        """

        if comp_type in self.ids:
            slot_info = self.ids[comp_type]
        else:
            slot_info = nooobs.SlotTracker()
            self.ids[comp_type] = slot_info

        if slot_info.on_deck.empty():
            id_type = nooobs.id_map[comp_type]
            id = id_type(slot_info.next_slot, 0)
            slot_info.next_slot += 1
            return id
        else:
            return slot_info.on_deck.get() 


    