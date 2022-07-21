import noodle_objects

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
            ("update", None): 31,
            ("reset", None): 32,
            ("invoke", noodle_objects.Signal): 33,
            ("reply", noodle_objects.Method): 34,
            ("initialized", None): 35,
        }

        # Set up hardcoded state for initial testing
        for key, value in hardcoded_state.items():
            self.objects[key] = value

    def prepare_message(self, action: str, object):

        # Get ID for message
        id = self.message_map[(action, type(object))]

        # Get message contents
        contents = {}
        if action == "create":
            pass

        elif action == "update":

            # Document case
            if object == None:
                contents["methods_list"] = self.objects["methods"].keys()
                contents["signals_list"] = self.objects["signals"].keys()
            # Normal update
            else:
                pass

        elif action == "delete":
            contents["id"] = object.id

        elif action == "invoke":
            pass

        elif action == "reply":
            pass

        elif action == "initialized" or action == "reset":
            pass


        return id, contents


    async def handle_intro(self, websocket):

        # Send appropriate messages for new client
        message = []
        for specifier, object_map, in self.objects.items():
            for id, object in object_map.items():
                id, content = self.prepare_message("create", object)
                message.append(id, content)

        print(f"Message sent to handle new client: {message}")
        await websocket.send(message)