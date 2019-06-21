1. First start up the all-in-one Jaeger demonstrator container:
   ```
   podman run --rm -p 6831:6831/udp -p 6832:6832/udp -p 16686:16686 jaegertracing/all-in-one --log-level=debug
   ```
   (You can substiture "docker" for "podman" if you have docker not podman as your container runtime)

   Note that we are running Jaeger purely in memory with no persistent storage. Any traces we collect will be gone as soon as we interrupt or stop the container.

1. Now we need to set up the python environment. For this purpose we're using pipenv, so make sure you have it installed. If not, you can use
   ```
   pip3 install --user pipenv
   ```
   to install it (depending on your installation use `pip` not `pip3`).

   Making sure we are in the WorkedExample directory, now run:
   ```
   pipenv install
   ```
   This ensures that we have a python environment with the modules necessary to run our examples. Now running
   ```
   pipenv shell
   ```
   Makes that environment the default - we could use `pipenv run` for each individual python command, but we are going to start several.

   [You will probably want to start multiple terminals or tabs for the various different programs running. Make sure you run `pipenv shell` in each of them so that they all have the correct python environment]

1. Now start up a web browser and point it to http://localhost:16686/. This should open up a console for the Jaeger tracing system.


1. Demo with a simple sender and direct receiver:

   In different windows run:
   ```
   python direct_recv.py
   ```
   and
   ```
   python simple_send.py
   ```
1. Go to the Jaeger console and search for traces from service 'direct_recv'.

1. More interesting demo with broker.
   For this we are using an example broker in python.

   In one window run:
   ```
   python broker.py
   ```
   In another run:
   ```
   python simple_recv.py
   ```
   In the final window:
   ```
   python simple_send.py
   ```
1. Again goto to Jaeger console and search for traces - this time from service 'simple_recv'.

1. Yet more interesting trace with broker
   This is interesting because it shows an RPC like interaction using reliable messaging over a broker. The top level RPC is a single span encompassing all of the following action.

   Keep the broker runnning from the previous demo.

   In one window run
   ```
   python server.py
   ```
   In another run
   ```
   python client.py
   ```
1. Now go to the Jaeger console again and search for service 'server'



