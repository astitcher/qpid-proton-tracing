# Plan

Ideally we want to produce a tracing environment that works with no user intervention,
so that we could automatically get tracing relationships between messages being passed
around a distributed system.

## Need to model a span:
These are some intial thoughts for some more depth see [WorkingNotes]
- Unlike RPCs general async messages don't have a natural span.
- Possibilities:
  - Span from send to settlement of delivery - annotate with disposition modifications
    - Is that different from span from send to ack/nack?
    - This doesn't seem to create a span that would for example encompass a pub/sub
      subscription. As the deliveries are different. It should connect all the spans though by making the subsequent messages children.
    - It is possible to automate the span creation/destruction, especially as span are managed at a single node.
  - Span from initial send of a correlation id or equivalent to final settlement of message with that correlation id.
    - It appears to be hard to figure that out automatically. Especially as the spans would often start and end on different nodes.
  - Aside: As long as the nodes don't keep track of all their spans it shouldn't matter if we create and destroy them in different places, but if we do keep track of them then it makes it hard.
  - For RPC like interactions -  Request/Response we can create a high level abstraction that models spans like RPC. But it's not obvious that this is so useful.

## Minimal Pieces
- Code to insert/extract span/parent span id to message.
  - Inserting at the lowest (Proton-c) level probably just takes the two ids and adds them to the correct message properties. Probably makes sense to do this in C for reuse although that's not 100% clear as the operation is pretty simple, but want this to be very cheap if turned on.
  - This piece can be pretty much automatic if turned on in the binding API. So we can inherit any span id in the current context as a parent id when creating a new message. And we can set the span id in the context of a message handler to be the span id of the message being handled. Although some/all of the automaticness would be implemented in the higher level API.
- Code to create/destroy spans.
  - This probably goes with the insert/extract spans code. However as it necessitates talking to the OpenTracing API it is probably in the higher level code which is controlling tracing.
  - As above what point to close a span is an interesting discussion point. Perhaps the scheme used could be an option. Although doing this makes it harder to make this really automatic and easy for a user.

Once we have the above bits in out bindings say Python and C++ initially then applications ahould be able to use tracing for their own purposes. They would have to turn it on using some Proton API and then use OpenTracing APIs to add their own annotations etc. But with these bits you could get useful application level traces out of Jaeger etc.

However this would give you no insight into the behaviour of network and messaging elements (Routers and Broker).

## More Pieces
- So to be most useful we need to be addding tracing to the router and the broker so that they extract the span ids and annotate them with relevant info.
- For the broker this is probably things like additional spans for directing to queues, queuing, dequeing.
- For the router it would be similar. However the router has a technical issue in that it is written in C and Opentracing has no official C API, although there is a C API that is available it is not clear how well maintained it is.

[WorkingNotes]: WorkingNotes.md
