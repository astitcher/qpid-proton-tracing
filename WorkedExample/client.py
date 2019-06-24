#!/usr/bin/env python
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

from __future__ import print_function, unicode_literals
import optparse
from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container, DynamicNodeProperties

from tracing import init_tracer, fini_tracer, trace_consumer_handler, trace_send, trace_settle

tracer = init_tracer('client')

class Client(MessagingHandler):
    def __init__(self, url, requests):
        super(Client, self).__init__()
        self.url = url
        self.requests = requests
        self.spans = []
        for r in requests:
            tags = { 'request': r}
            span = tracer.start_span('request', ignore_active_span=True, tags=tags)
            span.log_kv({'event': 'request_created'})
            self.spans.append(span)

    def on_start(self, event):
        self.sender = event.container.create_sender(self.url)
        self.receiver = event.container.create_receiver(self.sender.connection, None, dynamic=True)

    def next_request(self):
        if self.receiver.remote_source.address:
            req = self.requests[0]
            span = self.spans[0]
            with tracer.scope_manager.activate(span, False):
                span.log_kv({'event': 'request_sent'})
                msg = Message(reply_to=self.receiver.remote_source.address, body=req)
                trace_send(tracer, self.sender, msg)

    def on_settled(self, event):
        trace_settle(tracer, event.delivery)

    def on_link_opened(self, event):
        if event.receiver == self.receiver:
            self.next_request()

    @trace_consumer_handler(tracer)
    def on_message(self, event):
        reply = event.message.body
        req = self.requests.pop(0)
        span = self.spans.pop(0)
        span.log_kv({'event': 'reply-received', 'result': reply})
        span.finish()
        print("%s => %s" % (req, reply))
        if self.requests:
            self.next_request()
        else:
            event.connection.close()

REQUESTS= ["Twas brillig, and the slithy toves",
           "Did gire and gymble in the wabe.",
           "All mimsy were the borogroves,",
           "And the mome raths outgrabe."]

parser = optparse.OptionParser(usage="usage: %prog [options]",
                               description="Send requests to the supplied address and print responses.")
parser.add_option("-a", "--address", default="localhost:5672/examples",
                  help="address to which messages are sent (default %default)")
opts, args = parser.parse_args()

Container(Client(opts.address, args or REQUESTS)).run()

fini_tracer(tracer)
