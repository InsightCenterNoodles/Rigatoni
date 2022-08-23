"""Module with core implementation of Server Object"""

from __future__ import annotations
from types import NoneType
from typing import TYPE_CHECKING, Type, Union
if TYPE_CHECKING:
    from . import interface

import websockets
from cbor2 import dumps

from . import noodle_objects as nooobs

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

    def __init__(self, starting_state: list[nooobs.StartingComponent], 
        delegates: dict[Type[nooobs.Component], Type[interface.Delegate]]):
        """Constructor
        
        Args: 
            methods (dict): 
                maps method names to the functions to be injected
            starting_state (list[nooobs.StartingComponent]):
                list of objects containing the info to create components on initialization
            delegates (dict):
                maps noodles component type to instance of delegate class

        Raises:
            Exception: Invalid Arguments or Method Not Specified when filling in starting state
        """

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

        # Set up starting state
        for starting_component in starting_state:
            comp_type = starting_component.type
            comp_method = starting_component.method
            try:
                comp = self.create_component(comp_type, **starting_component.component_attrs)
            except:
                raise Exception(f"Invalid arguments to create {comp_type}")

            if comp_type == nooobs.Method:
                if comp_method == None:
                    raise Exception("Method not specified for starting method")
                else:
                    injected = nooobs.InjectedMethod(self, comp_method)
                    setattr(self, comp.name, injected)


    def get_ids_by_type(self, component: Type[nooobs.Component]) -> list:
        """Helper to get all ids for certain component type
        
        Args:
            comp (type): type of component to get ID's for
        """

        return [key for key, val in self.components.items() if isinstance(val, component)]


    def get_component_id(self, type: Type[nooobs.Component], name: str):
        """Helper to get a component with a type and name"""

        for id, comp in self.components.items():
            if isinstance(comp, type) and hasattr(comp, "name") and comp.name == name:
                return id
        raise Exception("No Component Found")


    def get_component(self, id: nooobs.ID):
        """Getter for users to acces components in state"""

        try:
            return self.components[id].copy(deep=True)
        except:
            raise Exception("No Component Found")


    def get_message_contents(self, action: str, 
        object: nooobs.NoodleObject=None, delta: set[str]={}):
        """Helper to handle construction of message dict
        
        Args:
            action (str): action taken with message
            object (NoodleObject): Component, Reply, or Invoke object
            delta (set): field names to be included in update
        """

        contents = {}
        if action in {"create", "invoke", "reply"}:
            contents = object.dict(exclude_none=True)

        elif action == "update":
            if object == None: # Document case
                contents["methods_list"] = self.get_ids_by_type(nooobs.Method)
                contents["signals_list"] = self.get_ids_by_type(nooobs.Signal)
            else: # Normal update, include id, and any field in delta
                delta.add("id")
                contents = object.dict(exclude_none=True, include=delta)

        elif action == "delete":
            contents["id"] = object.id

        return contents


    def prepare_message(self, action: str, 
        object: nooobs.NoodleObject=None, delta: set[str]={}):
        """Given object and action, get id and message contents as dict

        Args:
            action (str): action taken with message
            object (NoodleObject): Component, Reply, or Invoke object
            delta (set): field names to be included in update
        """

        id = self.message_map[(action, type(object))]
        contents = self.get_message_contents(action, object, delta)

        return id, contents


    def broadcast(self, message: list):
        """Broadcast message to all connected clients
        
        Args:
            message [list]: fully constructed message in list form
        """
        
        print(f"Broadcasting Message: ID's {message[::2]}")
        encoded = dumps(message)
        websockets.broadcast(self.clients, encoded)


    def handle_intro(self):
        """Formulate response for new client"""

        # Add create message for every object in state
        message = []
        ordered_components = order_components(self.components, self.references)
        for object in ordered_components:
            msg_id, content = self.prepare_message("create", object)
            message.extend([msg_id, content])

        # Add document update
        message.extend(self.prepare_message("update", None))
        
        # Finish with initialization message
        message.extend(self.prepare_message("initialized"))    
        return message


    def handle_invoke(self, message: dict):
        """Handle all invokes coming from the client
        
        Take message and formulate response for clients. Tryies to invoke and 
        raises appropriate error codes if unsuccessful. Note that the method 
        technically doesn't raise any exceptions, instead the exception is 
        captured in a message and sent to the client.
        
        Args:
            message (dict): dict form of message from client
        """

        # Create generic reply with invalid invoke ID and attempt invoke
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
        """Invoke method and build out reply object
        
        Mostly a helper for handle_invoke to raise proper method exceptions

        Args:
            message (dict): Invoke message in dict form
            reply (Reply): Practically empty reply object to be updated 
        """
        
        # Parse message
        try:
            method_id = nooobs.MethodID(slot=message["method"][0], gen=message["method"][1])
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
    

    def update_references(self, comp: nooobs.Component, current: nooobs.NoodleObject, removing=False):
        """Update indegree for all objects referenced by this one

        Recursively updates references for all components under a parent one. Here,
        the current object changes through the recursion while comp keeps track of 
        the parent 
        
        Args:
            comp (Component): parent component with new references to be tracked
            current (NooodleObject): current object being examined
            removing (bool): flag so function can be used to both add and remove references
        """

        for key in current.__fields__.keys():
            val = getattr(current, key)

            # Found a reference
            if key != "id" and isinstance(val, nooobs.ID):
                if removing:
                    self.references[val].remove(comp.id)
                else:
                    self.references.setdefault(val, set()).add(comp.id)

            # Found another object to recurse on
            elif isinstance(val, nooobs.NoodleObject):
                self.update_references(comp, val, removing)

            # found list of objects to recurse on 
            elif val and isinstance(val, list) and isinstance(val[0], nooobs.NoodleObject):
                for obj in val:
                    self.update_references(comp, obj, removing)


    def get_id(self, comp_type: Type[nooobs.Component]) -> nooobs.IDGroup:
        """Get next open ID
        
        Check for open slots then take closest available slot

        Args:
            comp_type (Component Type): type for desired ID
        """

        if comp_type in self.ids:
            slot_info = self.ids[comp_type]
        else:
            slot_info = nooobs.SlotTracker()
            self.ids[comp_type] = slot_info

        if slot_info.on_deck.empty():
            id_type = nooobs.id_map[comp_type]
            id = id_type(slot=slot_info.next_slot, gen=0)
            slot_info.next_slot += 1
            return id
        else:
            return slot_info.on_deck.get() 
        

    # Interface methods to build server methods ===============================================
    def create_component(self, comp_type: Type[nooobs.Component], **kwargs) -> nooobs.Component:
        """Officially create new component in state
        
        This method updates state, updates references, and broadcasts msg to clients.
        It also handles the acquisition of a valid ID
        
        Args:
            comp_type (Component Type): type of component to be created
            **kwargs: the user should specify the attributes of the component using 
                keyword arguments. Refer to the noodle objects to see which attributes
                are required and optional. Any deviation from the spec will raise a 
                validation exception. Note that since this method handles the ID, it 
                should not be specified as one of the keword arguments.
        """

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

    def delete_component(self, obj: Union[nooobs.Component, interface.Delegate, nooobs.ID]):
        """Delete object in state and update clients
        
        This method excepts a delegate, component, or component ID, and will attempt
        to delete the component as long as it is not referenced by any other component.
        If this component is still being used by another, it will be added to a queue so
        it can be deleted later once that refernece is no longer being used.

        Args:
            obj (Component, Delegate, or ID): component / delegate to be deleted
        """

        # Handle cases so can except different input types
        if type(obj) in self.custom_delegates.values():
            id = obj.component.id
            del self.delegates[id]
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
            for comp_id in list(self.delete_queue):
                if not self.references.get(comp_id):
                    self.delete_queue.remove(comp_id)
                    self.delete_component(comp_id)

        else:
            if isinstance(obj, nooobs.ID):
                print(f"Couldn't delete {self.components[obj]}, referenced by {self.references[id]}, added to queue")
            else:
                print(f"Couldn't delete {obj}, referenced by {self.references[id]}, added to queue")
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
                self.update_references(state, state_val, removing=True)
                self.update_references(edited, value)

        return delta

    
    def update_component(self, obj: nooobs.Component):
        """Update clients with changes to a component
        
        This method broadcasts changes to all clients including only fields
        specified in the set delta

        Args:
            obj (Component): component that has been updated, 
                should be a component with an update message
            delta (Set): Field names that should be included in the update
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


    def invoke_signal(self, signal: nooobs.ID, on_component: nooobs.Component, signal_data: list):
        """Send signal to target component
        
        Args:
            signal (ID): signal to be invoked
            on_component (Component): component to receive the signal
            signal_data (dict): 
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
        else:
            raise Exception(f"Invalid on_component type: {type(on_component)}")

        # Create invoke object and broadcast message
        invoke = nooobs.Invoke(id=signal, context=context, signal_data=signal_data)
        message = self.prepare_message("invoke", invoke)
        self.broadcast(message)


def top_sort_recurse(id, refs, visited, components, stack):
    """Helper for order_components to recurse"""

    visited[id] = True
    if id in refs:
        for ref in refs[id]:
            if not visited[ref]:
                top_sort_recurse(ref, refs, visited, components, stack)

    stack.append(components[id])


def order_components(components: dict[nooobs.ID, nooobs.Component], 
    refs: dict[nooobs.ID, list[nooobs.ID]]):
    """Helper for creating topological sort of components"""

    visited = {key: False for key in components}
    stack = []

    for id in components:
        if not visited[id]:
            top_sort_recurse(id, refs, visited, components, stack)
    
    return stack[::-1]
