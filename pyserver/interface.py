"""Interface Methods for Specific Components"""
from typing import Optional
from .core import Server
from . import noodle_objects as nooobs


# def create_method(server: Server, name: str, 
#                   doc: Optional[str]=None, return_doc: Optional[str]=None, 
#                   arg_doc: Optional[list[nooobs.MethodArg]]= None):

#     component_type = nooobs.Method
#     id = server.get_id(component_type)

#     method = nooobs.Method(id, name, doc, return_doc, arg_doc)
#     component = server.create_object(component_type, method)

#     return component


class ServerTableDelegate(object):

    def __init__(self, server: Server, component: nooobs.Component):
        self.server = server
        self.component = component
        self.selection = {}

    def handle_insert(self, new_rows: list[list[int]]):
        pass

    def handle_update(self, keys: list[int], rows: list[list[int]]):
        pass

    def handle_delete(self, keys: list[int]):
        pass

    def handle_clear(self):
        pass

    def handle_set_selection(self, selection: nooobs.Selection):
        pass


    # Signals ---------------------------------------------------
    def table_reset(self, tbl_init: nooobs.TableInitData):
        """Invoke table reset signal"""
        pass
    

    def table_updated(self, keys: list[int], rows:list[list[int]]):
        pass


    def table_rows_removed(self, keys: list[int]):
        pass


    def table_selection_updated(self, selection: nooobs.Selection):
        pass