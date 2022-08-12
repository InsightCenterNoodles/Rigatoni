"""Test script to work with penne's test client

Roughly modeled off of PlottyN, this script shows how a user
could overwrite the table delegate to add table functionality
"""

import asyncio
import weakref

import pandas as pd

from context import rigatoni
from rigatoni.server import start_server
from rigatoni.core import Server
import rigatoni.noodle_objects as nooobs
import rigatoni.interface as interface

def new_point_plot(server: Server, context: dict, xs, ys, zs, colors=None, sizes=None):

    # Create component and state and get delegate reference
    tbl_delegate: CustomTableDelegate = server.create_component(
        nooobs.Table, 
        name="Custom Table", 
        meta="Table for testing", 
        methods_list=[
            server.get_component_id(nooobs.Method, "noo::tbl_subscribe"),
            server.get_component_id(nooobs.Method, "noo::tbl_insert")
        ], 
        signals_list=[
            server.get_component_id(nooobs.Signal, "noo::tbl_reset"),
            server.get_component_id(nooobs.Signal, "noo::tbl_updated"),
            server.get_component_id(nooobs.Signal, "noo::tbl_rows_removed"),
            server.get_component_id(nooobs.Signal, "noo::tbl_selection_updated")
        ]
    )

    # Set default colors and sizes 
    if not colors:
        colors = [0.0, 0.0, 0.0] * len(xs)
    if not sizes:
        sizes = [[.02, .02, .02] for i in xs]
    # Get values for dataframe
    color_cols = list(zip(*colors))
    size_cols = list(zip(*sizes))

    data = {
        "x": xs, 
        "y": ys, 
        "z": zs, 
        "r": color_cols[0], 
        "g": color_cols[1], 
        "b": color_cols[2], 
        "sx": size_cols[0], 
        "sy": size_cols[1], 
        "sz": size_cols[2],
        "": [''] * len(xs)
    }

    tbl_delegate.dataframe = pd.DataFrame(data)
    print(tbl_delegate.dataframe)
 
    return 1


def subscribe(server: Server, context: dict):

    # Try to get delegate from context
    try:
        tbl_id = nooobs.TableID(*context["table"])
        delegate: CustomTableDelegate = server.delegates[tbl_id]
    except:
        raise Exception(nooobs.MethodException(code=-32600, message="Invalid Request - Invalid Context for Subscribe"))
    
    tbl: pd.DataFrame = delegate.dataframe
    types = ["REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "TEXT"]

    # Arrange col info
    col_info = [nooobs.TableColumnInfo(name=col, type=type) for col, type in zip(tbl.columns, types)]
    
    # Formulate response info for subscription
    init_info = nooobs.TableInitData(columns=col_info, keys=tbl.index.values.tolist(), data=tbl.values.tolist())

    print(f"Init Info: {init_info}")
    return init_info

def insert(server: Server, context: dict, rows: list[list]):
    
    try:
        tbl_id = nooobs.TableID(*context["table"])
        delegate: CustomTableDelegate = server.delegates[tbl_id]
    except:
        raise nooobs.MethodException(-32600, "Invalid Request - Invalid Context for insert")

    # Allow for rows without annotations
    for row in rows:
        if len(row) == 9:
            row.extend([''])

    # Update state in delegate
    keys = delegate.handle_insert(rows)
    print(f"Inserted @ {keys}, \n{delegate.dataframe}")

    # Send signal to update client
    delegate.table_updated(keys, rows)

    return keys

starting_state = [
    nooobs.StartingComponent(nooobs.Method, {"name": "new_point_plot", "arg_doc":[]}, new_point_plot), 
    nooobs.StartingComponent(nooobs.Method, {"name": "noo::tbl_subscribe", "arg_doc":[]}, subscribe), 
    nooobs.StartingComponent(nooobs.Method, {"name": "noo::tbl_insert", "arg_doc":[]}, insert), 
    nooobs.StartingComponent(nooobs.Method, {"name": "Test Method 4", "arg_doc":[]}, print), 

    nooobs.StartingComponent(nooobs.Signal, {"name": "noo::tbl_reset", "arg_doc":[]}),
    nooobs.StartingComponent(nooobs.Signal, {"name": "noo::tbl_updated", "arg_doc":[]}),
    nooobs.StartingComponent(nooobs.Signal, {"name": "noo::tbl_rows_removed", "arg_doc":[]}),
    nooobs.StartingComponent(nooobs.Signal, {"name": "noo::tbl_selection_updated", "arg_doc":[]})
]


class CustomTableDelegate(interface.ServerTableDelegate):

    def __init__(self, server: Server, component: weakref.ReferenceType):
        super().__init__(server, component)
        self.dataframe = pd.DataFrame()


    def handle_insert(self, rows: list[list[int]]):

        next_index = self.dataframe.index[-1] + 1
        new_index = range(next_index, next_index + len(rows))

        new_df = pd.DataFrame(rows, columns=self.dataframe.columns.values, index=new_index)
        self.dataframe = pd.concat([self.dataframe, new_df])
        
        return list(new_index)


    def handle_update(self, keys: list[int], rows: list[list[int]]):
        
        for key, row in zip(keys, rows):
            self.dataframe.loc[key] = row
        
        return keys


    def handle_delete(self, keys: list[int]):
        
        self.dataframe.drop(index=keys, inplace=True)

        return keys


    def handle_clear(self):
        
        self.dataframe = pd.DataFrame()
        self.selections = {}


    def handle_set_selection(self, selection: nooobs.Selection):

        self.selections[selection.name] = selection

    # Signals ---------------------------------------------------
    def table_reset(self, tbl_init: nooobs.TableInitData):
        """Invoke table reset signal"""

        data = [tbl_init]

        signal = self.server.get_component_id(nooobs.Signal, "noo::tbl_reset")
        self.server.invoke_signal(signal, self.component, data)


    def table_updated(self, keys: list[int], rows:list[list[int]]):

        data = [keys, rows]

        signal = self.server.get_component_id(nooobs.Signal, "noo::tbl_updated")
        self.server.invoke_signal(signal, self.component, data)


    def table_rows_removed(self, keys: list[int]):
        
        data = [keys]

        signal = self.server.get_component_id(nooobs.Signal, "noo::tbl_rows_removed")
        self.server.invoke_signal(signal, self.component, data)


    def table_selection_updated(self, selection: nooobs.Selection):
    
        data = [selection]

        signal = self.server.get_component_id(nooobs.Signal, "noo::tbl_selection_updated")
        self.server.invoke_signal(signal, self.component, data)



delegates = {
    nooobs.Table: CustomTableDelegate,
}


def main():
    asyncio.run(start_server(50000, starting_state, delegates))

if __name__ == "__main__":
    main()