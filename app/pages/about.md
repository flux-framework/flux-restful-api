# Flux RESTFul API

This is a small Flux Python API (using FastAPI) that can be containerized
alongside Flux, and provide an easy means to interact with Flux via the API.
My goals are:

1. provide simple endpoints to submit jobs, list jobs, or get job status
2. eventually support subscribing to events
3. option to kill or stop the server (intended for Flux Operator)
4. allow for start with a user name and token (for basic auth)

The assumption for my use case is that we deploy this on the fly,
alongside a Flux broker, and we only need to authenticate for the single
user case. For the Flux Operator, if we can start a mini-cluster running
a server and then submit jobs to it and have it taken down by API call,
that would be really cool (and is what I plan to test.)
