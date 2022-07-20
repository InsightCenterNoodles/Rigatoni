class Server(object):
    """NOODLES Server
    
    Attributes;
        clients (dict): map clients to connection
        reference_graph (dict): map object id to references
        ids (dict): keep track of available slots
    """

    def __init__(self):
        self.clients = {}
        self.reference_graph = {}
        self.ids = {}