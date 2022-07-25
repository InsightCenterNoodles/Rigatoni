import asyncio

from pyserver.noodle_objects import Method
from pyserver.server import start_server
import pyserver.noodle_objects as nooobs
from pyserver.core import Server

def new_point_plot(server, col1, col2, col3, colors=None, sizes=None):
    
    id = server.get_id(nooobs.Table)
    method_list = []
    signal_list = []
    tbl = nooobs.Table(id, "Test Table", "Table for testing", method_list, signal_list)
    server.create_object(tbl)

    return id

    #raise Exception("BLAH")

methods = {
    'new_point_plot': new_point_plot
}

starting_state = {
    nooobs.Method: {
        nooobs.IDGroup(0,0): Method((0,0), "new_point_plot"),
        nooobs.IDGroup(1, 0): Method((1,0), "Test Method 2"),
        nooobs.IDGroup(2, 0): Method((2,0), "Test Method 3"),
        nooobs.IDGroup(3, 0): Method((3,0), "Test Method 4"),
    }
}


def main():
    asyncio.run(start_server(50000, methods, starting_state))

if __name__ == "__main__":
    main()