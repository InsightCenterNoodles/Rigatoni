# What is NOODLES?

NOODLES is a messaging protocol for shared interactive visualizations. The protocol sets standards
for developing client and server libraries which serve as the bridge between various applications. 

The Server Library presents a visualization to one or more connected clients through a synchronized 
scenegraph. Client requests and messages are passed on for handling to the application code, which 
can manipulate the scenegraph in response. These changes are then published and sent to clients.

The Client Library connects to a server, and maintains the synchronized scenegraph. This scenegraph 
is query-able by the client. Clients then can interpret and present the scenegraph to the user in the 
way they see fit. For example, an immersive graphics engine client can draw the scenegraph as is, while 
a 2D client can choose to present only a subset of the graph. A command line (i.e. Python) client may 
ignore the scenegraph completely to merely make use of the messaging and method invocation functionality. 
This also allows each client to customize the interactions available in a way that best aligns with 
their form factor.

Below is a graph which illustrates the structure a NOODLES session and the way entities are composed in
general.

![NOODLES Entity Structure](assets/concepts.svg)


# More Info

- [Full Message Specification](https://github.com/InsightCenterNoodles/message_spec)
- [More Client and Server Libraries](https://github.com/InsightCenterNoodles)