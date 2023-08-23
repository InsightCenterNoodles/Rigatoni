Installation is as simple as:

```bash
pip install rigatoni
```

Rigatoni has a few dependencies:

* [`websockets`](https://websockets.readthedocs.io/en/stable/): Websocket connections in Python.
* [`cbor2`](https://cbor2.readthedocs.io/en/latest/): Concise Binary Object Representation for messages.
* [`pydantic`](https://docs.pydantic.dev/dev-v2/): Data validation and coercion for parsing messages.

If you've got Python 3.9+ and `pip` installed, you're good to go.

## Optional dependencies

Pydantic has the following optional dependencies:

* If you require support for meshes and geometry object creation, you can add 
[numpy](https://numpy.org/doc/stable/index.html) and [meshio](https://github.com/nschloe/meshio) 

To install optional dependencies along with Rigatoni:

```bash
pip install rigatoni[geometry]
```

!!! Note

    For stability, Rigatoni's core dependencies are pinned to specific versions. While these are up to date as of August
    2023, you may want to update them to the latest versions. To do so, simply update the package yourself.
