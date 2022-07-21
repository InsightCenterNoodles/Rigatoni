from dataclasses import fields
from types import NoneType
import noodle_objects
from cbor2 import dumps

class Server(object):
    """NOODLES Server
    
    Attributes;
        clients (dict): map clients to connection
        reference_graph (dict): map object id to references
        ids (dict): keep track of available slots
    """

    def __init__(self, hardcoded_state):
        self.clients = set()
        self.reference_graph = {}
        self.ids = {}
        self.objects = {
            "entities": {},
            "tables": {},
            "plots": {},
            "signals": {},
            "methods": {},
            "materials": {},
            "geometries": {},
            "lights": {},
            "images": {},
            "textures": {},
            "samplers": {},
            "buffers": {},
            "bufferviews": {}
        }
        self.message_map = {
            ("create", noodle_objects.Method): 0,
            ("delete", noodle_objects.Method): 1,
            ("create", noodle_objects.Signal): 2,
            ("delete", noodle_objects.Signal): 3,
            ("create", noodle_objects.Entity): 4,
            ("update", noodle_objects.Entity): 5,
            ("delete", noodle_objects.Entity): 6,
            ("create", noodle_objects.Plot): 7,
            ("update", noodle_objects.Plot): 8,
            ("delete", noodle_objects.Plot): 9,
            ("create", noodle_objects.Buffer): 10,
            ("delete", noodle_objects.Buffer): 11,
            ("create", noodle_objects.BufferView): 12,
            ("delete", noodle_objects.BufferView): 13,
            ("create", noodle_objects.Material): 14,
            ("update", noodle_objects.Material): 15,
            ("delete", noodle_objects.Material): 16,
            ("create", noodle_objects.Image): 17,
            ("delete", noodle_objects.Image): 18,
            ("create", noodle_objects.Texture): 19,
            ("delete", noodle_objects.Texture): 20,
            ("create", noodle_objects.Sampler): 21,
            ("delete", noodle_objects.Sampler): 22,
            ("create", noodle_objects.Light): 23,
            ("update", noodle_objects.Light): 24,
            ("delete", noodle_objects.Light): 25,
            ("create", noodle_objects.Geometry): 26,
            ("delete", noodle_objects.Geometry): 27,
            ("create", noodle_objects.Table): 28,
            ("update", noodle_objects.Table): 29,
            ("delete", noodle_objects.Table): 30,
            ("update", NoneType): 31,
            ("reset", NoneType): 32,
            ("invoke", noodle_objects.Signal): 33,
            ("reply", noodle_objects.Method): 34,
            ("initialized", NoneType): 35
        }

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
        if action == "create":
            contents = msg_from_obj(object)
        elif action == "update":

            # Document case
            if object == None:
                contents["methods_list"] = self.objects["methods"].keys()
                contents["signals_list"] = self.objects["signals"].keys()
            # Normal update
            else:
                msg_from_obj(object, delta)

        elif action == "delete":
            contents["id"] = object.id
            
        elif action == "invoke":
            assert(isinstance(object, noodle_objects.SignalInvokeMessage))
            contents = msg_from_obj

        elif action == "reply":
            assert(isinstance(object, noodle_objects.MethodReplyMessage))
            contents = msg_from_obj(object)

        elif action == "initialized" or action == "reset":
            pass


        return id, contents


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


    def handle_invoke(message: list):
        """Takes message and formulates response for clients"""

        method = message["method"]
        context = message.get("context")
        invoke_id = message["invoke_id"]
        args: list = message["args"]
        exception = None

        # What do you do here? how to invoke methods that user defines

        response = []
        result = []
        if exception:
            reply = noodle_objects.MethodReplyMessage(invoke_id, exception)
        else:
            reply = noodle_objects.MethodReplyMessage(invoke_id, result)
        return response, reply


def msg_from_obj(obj, delta: list[str]=None):
    """Return dict of all objects attributes that are not None"""

    if not delta: delta = [f.name for f in fields(obj)]

    contents = {}
    for field in fields(obj):
        val = getattr(obj, field.name)
        if val != None and field.name in delta:
            contents[field.name] = val
    return contents