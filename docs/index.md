# Flux RESTFul API

![Flux RESTFul API Logo](images/logo.png)

Welcome to the Flux RESTFul API!

This is a small Flux Python API (using FastAPI) that can be containerized
alongside Flux, and provide an easy means to interact with Flux via the API.
With Flux RESTful we can:

1. provide simple endpoints to submit jobs, list jobs, or get job status
2. eventually support subscribing to events with the user interface job table
3. OAuth2 flow with a user account and secret to retrieve tokens

There are three potential use cases:

1. No authentication: "I like to live dangerously."
2. Single-user authentication: "Use the default single account created by the server"
3. Multi-user authentication: "Add one or more users in addition to the superuser."

The authentication serves as a light wrapper to submitting jobs to Flux,
and there is not much more than that. The assumption for a "MiniCluster" use case
is that one or more users own an entire cluster and can submit jobs to
using the [Flux Operator](https://github.com/flux-framework/flux-operator).
This means that the Flux Operator creates and authenticates the server on
the fly, alongside a Flux broker. In the case of deploying alongside a more
production level Flux install, you likely want to expose the user interface
for cluster users. We will be adding back a PAM authentication flow to go
alongside with this, likely having users on the host match to server users.
Note that I (@vsoch) have not thought deeply about this use case yet, so
please [ping me](https://github.com/flux-framework/flux-restful-api/issues) if
you have ideas.

To get started, check out the links below!
Would you like to request a feature or contribute?
[Open an issue](https://github.com/flux-framework/flux-restful-api/issues).

```{toctree}
:maxdepth: 1
getting_started/index.md
tutorials/index
contributing.md
about/license
```

```{toctree}
:caption: API
:maxdepth: 1
source/modules.rst
```
