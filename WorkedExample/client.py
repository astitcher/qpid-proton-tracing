#!/usr/bin/env python3
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
import optparse
from opentracing import tags

from client_common import Client

from proton.reactor import Container

from proton.tracing import init_tracer

tracer = init_tracer('client')

REQUESTS= ["Twas brillig, and the slithy toves",
           "Did gire and gymble in the wabe.",
           "All mimsy were the borogroves,",
           "And the mome raths outgrabe."]

parser = optparse.OptionParser(usage="usage: %prog [options]",
                               description="Send requests to the supplied address and print responses.")
parser.add_option("-a", "--address", default="localhost:5672/examples",
                  help="address to which messages are sent (default %default)")
opts, args = parser.parse_args()

with tracer.start_active_span('client-requests') as context:
    # Force trace for this operation
    context.span.set_tag(tags.SAMPLING_PRIORITY, 1)
    Container(Client(opts.address, args or REQUESTS, tracer)).run()
