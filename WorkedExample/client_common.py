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
import uuid

from opentracing import global_tracer

from proton import Message
from proton.handlers import MessagingHandler
from proton.reactor import Container, DynamicNodeProperties

class Client(MessagingHandler):
    def __init__(self, url, requests):
        super(Client, self).__init__()
        self.url = url
        self.requests_queued = []
        self.requests_outstanding = {}
        for r in requests:
            self.add_request(r)

    def add_request(self, r):
        tags = { 'request': r}
        span = global_tracer().start_span('request', tags=tags)
        id = uuid.uuid4()
        self.requests_queued.append( (id, r, span) )

    def pop_request(self, id):
        return self.requests_outstanding.pop(id)

    def on_start(self, event):
        self.sender = event.container.create_sender(self.url)
        self.receiver = event.container.create_receiver(self.sender.connection, None, dynamic=True)

    def next_request(self):
        if self.receiver.remote_source.address:
            (id, req, span) = self.requests_queued.pop(0)
            with global_tracer().scope_manager.activate(span, False):
                span.log_kv({'event': 'request-sent'})
                msg = Message(reply_to=self.receiver.remote_source.address, correlation_id=id, body=req)
                self.sender.send(msg)
                self.requests_outstanding[id] = (req, span)

    def on_link_opened(self, event):
        if event.receiver == self.receiver:
            while len(self.requests_queued) > 0:
                self.next_request()

    def on_message(self, event):
        id = event.message.correlation_id
        reply = event.message.body
        (req, span) = self.pop_request(id)
        span.log_kv({'event': 'reply-received', 'result': reply})
        span.finish()
        print("%s => %s" % (req, reply))
        if self.requests_queued:
            self.next_request()
        elif len(self.requests_outstanding) == 0:
            event.connection.close()
