

Here is a basic example to get a plain server running with largely default components. The server will be initialized 
with one method to begin with, and the server will use the custom table delegate for each table in the scene. 
For more detailed examples, check out this [repo](https://github.com/InsightCenterNoodles/Rigatoni/tree/v0.2.1/tests/examples).

```python
import rigatoni as rig

class CustomTable(rig.Table):

    extra_info = None

    def handle_clear(self):
        print("Clearing table")

def basic_method(server, context):
    print("Hello World!")

starting_state = [
    rig.StartingComponent(rig.Method, {"name": "basic_method", "arg_doc": []}, basic_method),
]

delegates = {
    rig.Table: CustomTable
}

with rig.Server(50000, starting_state) as server:
    # do stuff
    pass
```