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

import functools
import time

import opentracing
import jaeger_client
from opentracing import follows_from as follows_from
from opentracing.ext import tags
from opentracing.propagation import Format

# Alias so we can use the name as a kw parameter
tfollows_from = follows_from

def init_tracer(service_name):
    config = jaeger_client.Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        service_name=service_name,
    )

    return config.initialize_tracer()

# A nasty hack to ensure enough time for the tracing data to be flushed
def fini_tracer(tracer):
    time.sleep(2)
    c = tracer.close()
    while not c.done:
        time.sleep(0.5)

def trace_consumer_handler(tracer):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, event):
            message = event.message
            receiver = event.receiver
            connection = event.connection
            span_ctx = tracer.extract(Format.TEXT_MAP, message.annotations)
            span_tags = {
                tags.SPAN_KIND: tags.SPAN_KIND_CONSUMER,
                tags.MESSAGE_BUS_DESTINATION: receiver.source.address,
                tags.PEER_ADDRESS: connection.connected_address,
                tags.PEER_HOSTNAME: connection.hostname,
                'inserted.automatically': 'message-tracing'
            }
            with tracer.start_active_span('amqp-delivery-receive', child_of=span_ctx, tags=span_tags):
                r = fn(self, event)

            return r
        return wrapper
    return decorator

def trace_send(tracer, sender, msg, child_of=None, follows_from=None):
    connection = sender.connection
    span_tags = {
        tags.SPAN_KIND: tags.SPAN_KIND_PRODUCER,
        tags.MESSAGE_BUS_DESTINATION: sender.target.address,
        tags.PEER_ADDRESS: connection.connected_address,
        tags.PEER_HOSTNAME: connection.hostname,
        'inserted.automatically': 'message-tracing'
    }
    if child_of is not None:
        span = tracer.start_span('amqp-delivery-send', tags=span_tags, child_of=child_of, ignore_active_span=True)
    elif follows_from is not None:
        span = tracer.start_span('amqp-delivery-send', tags=span_tags, references=[tfollows_from(follows_from.context)], ignore_active_span=True)
    else:
        span = tracer.start_span('amqp-delivery-send', tags=span_tags)
    headers = {}
    tracer.inject(span, Format.TEXT_MAP, headers)
    msg.annotations = headers
    delivery = sender.send(msg)
    delivery.span = span
    span.set_tag('delivery-tag', delivery.tag)
    return delivery

def trace_settle(tracer, delivery):
    delivery.span.finish()
