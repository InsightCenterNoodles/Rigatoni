"""Interface Methods for Specific Components"""
from .core import Server
from . import noodle_objects as nooobs


class ServerTableDelegate(object):

    def __init__(self, server):
        self._server = server



def handle_insert(server: Server, new_rows: list[list[int]]):
    pass

def handle_update(server: Server):
    pass

def handle_delete(server: Server):
    pass

def handle_reset(server: Server):
    pass

def handle_set_selection(server: Server):
    pass

def handle_(server: Server):
    pass


# Signals ---------------------------------------------------
def table_reset():
    pass

def table_selection_updated(selection):
    pass

def table_row_updated(keys: list[int], rows:list[list[int]]):
    pass

def table_row_deleted(keys: list[int]):
    pass