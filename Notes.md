Notes for message tracing for Proton based applications
=======================================================

- Assumption - we are going to use Jaeger as our tracing backend
  - As far as clients are concerned they use the OpenTracing API

- Consideration - where do tracing "ids" (spans) come from?
  - Really generating spans is an application level concern
  - Passing the tracing context around between elements of the distributed app is function of both tracing library and amqp implementation
  - Implement Inject/Extract capability for specific message transports.
  - Don't want to continually alter messages as they pass through routers and intermediaries as this may be expensive.
  - So do we record a span for messages passing through router/broker?
    - It's not obvious that we should as how would you choose the span name in other words this is perhaps not a real application level event.
    - Although you do want visibility of the time spent queuing/transitioning the interconnect
      - How would it work with istio?

  - So really want to generate when message is originally generated or piggyback on another
   identifier
  - Is there any AMQP TC consensus on how the tracing context gets attached to AMQP messages?


- What is the deliverable?
  - Demo?
  - Some sort of proton integration with Jaeger so that apps can pass around the tracing context?
  - New code in router/broker to record spans?
  - Some AMQP TC agreement/proposal for tracing context interoperation?

- C implementation og OpenTracing API
  - https://github.com/opentracing/opentracing-c

- Google Dapper
  - Google comment in their paper that they can use the tracing without explicit extra programming in the applications. They also talk about instrumenting low level libraries (used for amongst other things threading).
  
  - This is only possible because they already have an RPC abstraction/abstractions that they can instrument to form the spans and the relationships between them implicitly because of the flow of RPC events into various asynchrouns executions (local and remote)

  - This is not currently possible for us as we have no such RPC abstraction (At least in proton-c or anything using it).

  - Maybe Some things in JAva land have such an abstraction - Vrtx? In which case we could build some infrastructure like google to automatically put together RPC traces without application programmer overhead.

  - Even for the Google case (in 2010 at least) they comment that some number of their own systems use direct TCP or custom communication schemes and so can't transparently use the Dapper framework. These applications need some glue to connect to the Dapper tracing - we are currently in this situation.

  - *We should very definitely consider producing an RPC framework that can do OpenTracing transparently*
    - This would obviously require us to implement hooks into proton that can inject and extract tracing ids which is prerequisite for users to do the application work.
    - But we could also introduce our own RPC implementation using AMQP (or actually whatever) that transparently introduces the trace ids and transfers them over hte network so that tracing can be performed.

- Possible steps
  1. Prototype code that can inject/extract tracing ids from AMQP messages
     - Seems like this might be an addition to proton-c reusable by any of its users/
  2. New code in router/broker (elsewhere too? - EnMaas?) which uses the trace ids of incoming/outgoing messages to record trace spans for them as they are read from the network/queued and dequeued and written to the network.
     - Obviously the precise spans recorded here will depend on the exact function of the network elelment.
     - Any extra operations occuring to support the spans from incoming messages (for example messages sent for authentication or message routing purposes) should be recorded as related spans (hopefully in some way that can be automatic)
  3. Produce some sort of RPC mechanism that renders span generation automatic.
