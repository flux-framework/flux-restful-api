# Flux RESTFul API

![Flux RESTFul API Logo](images/logo.png)

Welcome to the Flux RESTFul API!

This is a small Flux Python API (using FastAPI) that can be containerized
alongside Flux, and provide an easy means to interact with Flux via the API.
With Flux RESTful we can:

1. provide simple endpoints to submit jobs, list jobs, or get job status
2. eventually support subscribing to events and a user interface job table
3. option to kill or stop the server (intended for Flux Operator)
4. allow for start with a user name and token (for basic auth)

The assumption for a "Mini Cluster" use case, where one user owns an entire cluster
and can submit jobs to it (see the [Flux Operator](https://github.com/flux-framework/flux-operator),
is that we deploy this on the fly, alongside a Flux broker, and we only need to
authenticate for the single user case. Given this setup, after deploying
the Mini Cluster the user can submit jobs to it (and have it taken down)
by way of a RESTful API call.

To get started, check out the links below!
Would you like to request a feature or contribute?
[Open an issue](https://github.com/flux-framework/flux-restful-api/issues).

```{toctree}
:maxdepth: 1
getting_started/index.md
auto_examples/index
contributing.md
about/license
```

```{toctree}
:caption: API
:maxdepth: 1
source/modules.rst
```
