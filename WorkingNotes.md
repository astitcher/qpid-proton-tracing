Working Notes
=============

* Opentracing != Jaeger
  - The Opentracing group provides APIs, but not useful implementations of those APIs. Essentially they are stubs with the API entry points but stub implementations
  - This explains my confusion with the Opentracing C API. It is not really a tracing API implementation rather just a stub implementation to be filled in.

* Span modelling
  - Spans model *operations* which do not correspond 1-1 with messages exactly. I think the spans for the pure AMQP message lifecycle are:
    - Sender side - Deliver Message
      - From Create message to receive terminal state (settle)
      - With potentially span logs for queuing/sending the message
        - perhaps relevant for multi-transfer messages
      - and any non-terminal updates to its state
    - Receiver side - Process incoming message (child of Deliver Message span unless message presettled in which case follows from)
      - From Receive message to settle delivery for message (NOT terminal state)
      - With potential span logs for sending terminal state disposition. The distinction here only matters for exactly-once, and in at-least-once the terminal state disposition will also settle the delivery.
      - Anything else going may reference the receive message span. For example in a broker queuing the message might be a child span which needs to complete before acknowledging the message. Equally, storing the message in a queue until it is forwarded to a subscriber might be a follows from span to either the initial receive message or queue message span.

  - So If there was a request-response (RPC) like interaction happening there would be a span for the overall RPC from initiation to answer with several child spans as above modelling the message interactions supporting the RPC.