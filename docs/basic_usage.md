
## Starting State

You can use starting component objects to help define the starting state

```python
rigatoni.StartingComponent(Type[Component], dict[Component_Attr, Value])
```

- You can refer to the objects listed [here](http://rigatoni.github.io/api_reference/components/) to find all the available delegates along with their 
mandatory, default, and optional attributes. Additional information on NOODLE components and their attributes can 
be found [here](https://github.com/InsightCenterNoodles/message_spec)
- When creating methods, an additional callable object should be attached. This method will be injected onto the 
server, and it will be associated with its corresponding method component.

```python
rigatoni.StartingComponent(Type[Component], dict[Component_Attr, Value], Callable)
```

## Defining Methods

To help with creating methods that manipulate the server's state, Rigatoni provides several methods that can be used
manage objects in the scene. More information on these methods can be found in the server section of the API reference
tab. Also, it is important to note that since each method is injected onto the server, they are called with a couple of 
arguments by default. The first two arguments to each method should always be the server object itself and 
a context. This provides easy access to essential information that can be used in the method.

## Delegates

The server comes with a default delegate class for each component that is maintained in the server's state. These
default delegates can be subclassed to add more functionality to each component in the scene. For example, the table 
delegate doesn't store any data by default, but users can customize it using any data structure they like. Below is a
simple example where the table delegate uses an added dataframe. A more complete version of this example can be found in
[here](https://github.com/InsightCenterNoodles/Rigatoni/blob/v0.2.1/tests/examples/basic_server.py).

```python
import pandas as pd
from rigatoni import Table

class CustomTableDelegate(Table):

    dataframe = pd.DataFrame()

    def handle_delete(self, keys: list[int]):
        self.dataframe.drop(index=keys, inplace=True)
        return keys
```

## Logging

Rigatoni uses the standard logging module for Python.
The logging level can be set by the user to any of the following:

- `logging.DEBUG`
- `logging.INFO`
- `logging.WARNING`
- `logging.ERROR`
- `logging.CRITICAL`

Here is a snippet you can use to toggle the logging level:
```python
import logging

logging.basicConfig(
    format="%(message)s",
    level=logging.DEBUG
)
```

## Run the Server

You can run the server indefinitely by calling `server.run()`. This will run until `server.shutdown()` is called.

```python
server = Server(50000, starting_state, delegates)
server.run() 
```
or alternatively, you can use a context manager to automatically start running the server in a new thread

```python
with Server(50000, starting_state, delegates) as server:
    # do stuff
```

