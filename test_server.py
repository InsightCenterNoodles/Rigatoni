import asyncio

import pandas as pd

from pyserver.noodle_objects import Method
from pyserver.server import start_server
from pyserver.core import Server
import pyserver.noodle_objects as nooobs
import pyserver.interface as interface

def new_point_plot(server: Server, context: dict, xs, ys, zs, colors=None, sizes=None):
    
    # Circle back to make better user method for getting method id from name
    subscribe = nooobs.IDGroup(1, 0)
    insert = nooobs.IDGroup(2, 0)

    # Create component and state and get delegate reference
    tbl_delegate: CustomTableDelegate = server.create_component(
        nooobs.Table, 
        name="Custom Table", 
        meta="Table for testing", 
        methods_list=[subscribe, insert], 
        signals_list=[nooobs.IDGroup(0, 0), nooobs.IDGroup(1, 0), nooobs.IDGroup(2, 0), nooobs.IDGroup(3, 0)]
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
        tbl_id = nooobs.IDGroup(*context["table"])
    except:
        raise nooobs.MethodException(-32600, "Invalid Request - Invalid Context for Subscribe")
    delegate: CustomTableDelegate = server.delegates[nooobs.Table][tbl_id]
    
    tbl: pd.DataFrame = delegate.dataframe
    types = ["REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "REAL", "TEXT"]

    # Arrange col info
    col_info = [nooobs.TableColumnInfo(name=col, type=type) for col, type in zip(tbl.columns, types)]
    
    # Formulate response info for subscription
    #data = list(map(list, df.itertuples(index=False)))
    #print(f"data: {data}")
    init_info = nooobs.TableInitData(columns=col_info, keys=tbl.index.values.tolist(), data=tbl.values.tolist())

    print(f"Init Info: {init_info}")
    return init_info

def insert(server: Server, context: dict, rows: list[list]):
    
    try:
        tbl_id = nooobs.IDGroup(*context["table"])
    except:
        raise nooobs.MethodException(-32600, "Invalid Request - Invalid Context for Subscribe")
    delegate: CustomTableDelegate = server.delegates[nooobs.Table][tbl_id]

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

# Client gets stuck cause there are now delete / update methods
methods = {
    "new_point_plot": new_point_plot,
    "noo::tbl_subscribe": subscribe,
    "noo::tbl_insert": insert
}

starting_state = {
    nooobs.Method: {
        nooobs.IDGroup(0, 0): Method(id=(0,0), name="new_point_plot"),
        nooobs.IDGroup(1, 0): Method(id=(1,0), name="noo::tbl_subscribe"), # Resume here... need keyword args
        nooobs.IDGroup(2, 0): Method(id=(2,0), name="noo::tbl_insert"),
        nooobs.IDGroup(3, 0): Method(id=(3,0), name="Test Method 4")
    },
    nooobs.Signal: {
        nooobs.IDGroup(0, 0): nooobs.Signal(id=(0,0), name="noo::tbl_reset"),
        nooobs.IDGroup(1, 0): nooobs.Signal(id=(1,0), name="noo::tbl_updated"),
        nooobs.IDGroup(2, 0): nooobs.Signal(id=(2,0), name="noo::tbl_rows_removed"),
        nooobs.IDGroup(3, 0): nooobs.Signal(id=(3,0), name="noo::tbl_selection_updated")
    }
}


class CustomTableDelegate(interface.ServerTableDelegate):

    def __init__(self, server: Server, component: nooobs.Component):
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

        signal = self.server.objects[nooobs.Signal][nooobs.IDGroup(0, 0)]
        self.server.invoke_signal(signal, self.component, data)


    def table_updated(self, keys: list[int], rows:list[list[int]]):

        data = [keys, rows]

        signal = self.server.objects[nooobs.Signal][nooobs.IDGroup(1, 0)]
        self.server.invoke_signal(signal, self.component, data)


    def table_rows_removed(self, keys: list[int]):
        
        data = [keys]

        signal = self.server.objects[nooobs.Signal][nooobs.IDGroup(2, 0)]
        self.server.invoke_signal(signal, self.component, data)


    def table_selection_updated(self, selection: nooobs.Selection):
    
        data = [selection]

        signal = self.server.objects[nooobs.Signal][nooobs.IDGroup(3, 0)]
        self.server.invoke_signal(signal, self.component, data)



delegates = {
    nooobs.Table: CustomTableDelegate
}


def main():
    asyncio.run(start_server(50000, methods, starting_state, delegates))

if __name__ == "__main__":
    main()