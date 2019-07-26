#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import atexit
import functools
import os
import sys
import time
import weakref

import opentracing
import jaeger_client
from opentracing.ext import tags
from opentracing.propagation import Format

import proton
from proton import Sender as ProtonSender
import proton.handlers
from proton.handlers import MessagingHandler as ProtonMessagingHandler

_tracer = None

def get_tracer():
    global _tracer
    if _tracer is None:
        _tracer = init_tracer(os.path.basename(sys.argv[0]))
    return _tracer

def _fini_tracer():
    time.sleep(2)
    c = opentracing.global_tracer().close()
    while not c.done:
        time.sleep(0.5)

def init_tracer(service_name):
    global _tracer
    config = jaeger_client.Config(
        config={},
        service_name=service_name,
        validate=True
    )
    _tracer = config.initialize_tracer()
    # A nasty hack to ensure enough time for the tracing data to be flushed
    atexit.register(_fini_tracer)
    return _tracer


# Message annotations must have symbols or ulong keys
# So convert string keys coming from tracer.inject to symbols
def _make_annotation(headers):
    r = {}
    for k, v in headers.items():
        r[proton.symbol(k)] = v
    return r

class IncomingMessageHandler(proton.handlers.IncomingMessageHandler):
    def on_message(self, event):
        if self.delegate is not None:
            tracer = get_tracer()
            message = event.message
            receiver = event.receiver
            connection = event.connection
            headers = message.annotations
            # Don't need to convert symbols to strings - they should be
            # automatically treated like strings anyway
            span_ctx = tracer.extract(Format.TEXT_MAP, headers)
            span_tags = {
                tags.SPAN_KIND: tags.SPAN_KIND_CONSUMER,
                tags.MESSAGE_BUS_DESTINATION: receiver.source.address,
                tags.PEER_ADDRESS: connection.connected_address,
                tags.PEER_HOSTNAME: connection.hostname,
                'inserted.automatically': 'message-tracing'
            }
            with tracer.start_active_span('amqp-delivery-receive', child_of=span_ctx, tags=span_tags):
                proton._events._dispatch(self.delegate, 'on_message', event)

class OutgoingMessageHandler(proton.handlers.OutgoingMessageHandler):
    def on_settled(self, event):
        if self.delegate is not None:
            delivery = event.delivery
            state = delivery.remote_state
            span = delivery.span
            span.log_kv({'event': 'delivery settled', 'state': state.name})
            span.finish()
            proton._events._dispatch(self.delegate, 'on_settled', event)

class MessagingHandler(ProtonMessagingHandler):
    def __init__(self, prefetch=10, auto_accept=True, auto_settle=True, peer_close_is_error=False):
        self.handlers = []
        if prefetch:
            self.handlers.append(proton.handlers.FlowController(prefetch))
        self.handlers.append(proton.handlers.EndpointStateHandler(peer_close_is_error, weakref.proxy(self)))
        self.handlers.append(IncomingMessageHandler(auto_accept, weakref.proxy(self)))
        self.handlers.append(OutgoingMessageHandler(auto_settle, weakref.proxy(self)))
        self.fatal_conditions = ["amqp:unauthorized-access"]

class Sender(ProtonSender):
    def send(self, msg):
        tracer = get_tracer()
        connection = self.connection
        span_tags = {
            tags.SPAN_KIND: tags.SPAN_KIND_PRODUCER,
            tags.MESSAGE_BUS_DESTINATION: self.target.address,
            tags.PEER_ADDRESS: connection.connected_address,
            tags.PEER_HOSTNAME: connection.hostname,
            'inserted.automatically': 'message-tracing'
        }
        span = tracer.start_span('amqp-delivery-send', tags=span_tags)
        headers = {}
        tracer.inject(span, Format.TEXT_MAP, headers)
        headers = _make_annotation(headers)
        msg.annotations = headers
        delivery = ProtonSender.send(self, msg)
        delivery.span = span
        span.set_tag('delivery-tag', delivery.tag)
        return delivery

# Monkey patch proton for tracing (need to patch both internal and external names)
proton._handlers.MessagingHandler = MessagingHandler
proton._endpoints.Sender = Sender
proton.handlers.MessagingHandler = MessagingHandler
proton.Sender = Sender
