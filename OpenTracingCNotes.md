Opentracing-C Notes
===================

At first glance this doesn't seem to provide anything except an Opentracing API in C. It seems to relies on external code to implement the actual tracer itself.

It 's not 100% clear to me at this point how you interface a tracer with this code - there seems to be some sort of dynamic loader for it - but I can't see how this works.

