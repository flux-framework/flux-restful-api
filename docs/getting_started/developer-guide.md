# Developer Guide

This developer guide includes complete instructions for setting up a developer
environment.

### Devcontainer

If you use VSCode a  [.devcontainer](https://github.com/flux-framework/flux-restful-api/tree/main/.devcontainer)
recipe is available that makes it easy to spin up an environment just by way of opening the repository in VSCode! After doing
this, continue to [Local](#Local) below.

### Docker

You can use the [demo container](https://github.com/flux-framework/flux-restful-api/pkgs/container/flux-restful-api),
either as provided or build on your own, to
run the server and interact with it. To optionally build the container:

```bash
$ docker build -t ghcr.io/flux-framework/flux-restful-api .
```

To build ensuring there is authentication (this will use user and token defaults)

```bash
$ docker build --build-arg use_auth=true -t ghcr.io/flux-framework/flux-restful-api .
```

Or define extra builds args `--build-arg user=fluxuser --build-arg token=12345` to customize the username and token!
Build arguments supported are:

| Name | Description | Default |
|------|-------------|---------|
| user | Username for basic auth | unset |
| token | Token password for basic auth | unset |
| use_auth | Turn on authentication | unset (meaning false) |
| port | Port to run service on (and expose) | 5000 |
| host | Host to run service on (you probably shouldn't change this) |0.0.0.0 |

And run it ensuring you expose port 5000. The container should show you if you've
correctly provided auth (or not):

```bash
$ docker run --rm -it -p 5000:5000 ghcr.io/flux-framework/flux-restful-api
```
```console
🍓 Require auth: True
🍓    Flux user: ********
🍓   Flux token: *****
INFO:     Started server process [72]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
```

Or run detached and then stop later:

```bash
$ docker run --name flux-restful -d --rm -it -p 5000:5000 ghcr.io/flux-framework/flux-restful-api
$ docker stop flux-restful
```

Either way, you can open your host to [http://127.0.0.1:5000](http://127.0.0.1:5000)
to see the very simple interface! This currently has API documentation ([openapi](https://fastapi.tiangolo.com/advanced/extending-openapi/))
and we will soon add a table of jobs.

![img/portal.png](img/portal.png)

Once you have the server running, you can test out the example scripts!
You'll minimally need requests installed:

```bash
$ pip install requests
```

Note there is more documentation about this in the user guide.
You should export the same flux user and password token if you added authentication:

```bash
$ export FLUX_USER=fluxuser
$ export FLUX_TOKEN=12345
```
```bash
$ python
```


See the [examples](examples) folder for more functionality.

### Local

You can use this setup locally (if you have flux and Python available) or within the Dev Container
in a VSCode environment.

#### 1. Install

Install dependencies:

```bash
$ python -m venv env
$ source env/bin/activate
$ pip install -r requirements.txt
```

Install requirements (note that you also need Flux Python available, which isn't in these requirements as you cannot install from pip).

```bash
$ pip install -r app-requirements.txt
```

#### 2. Start Service

There are two ways to start the app! You can either have it be the entry for flux start:

```console
$ flux start uvicorn app.main:app --host=0.0.0.0 --port=5000
```

Or do it separately (two commands):

```bash
$ flux start --test-size=4
$ uvicorn app.main:app --host=0.0.0.0 --port=5000
```

For the latter, you can also use the Makefile:

```bash
$ make
```
If you are developing, you must do the second approach as the server won't live-update
with the first.

#### 3. Authentication

If you want to require authentication for the user, export the user and token and
a variable that tells the server to use auth:

```bash
export FLUX_USER=$USER
export FLUX_TOKEN=123456
export FLUX_USER_AUTH=true
```

#### 4. Interactions

After starting, you can open your browser to [http://127.0.0.1:5000](http://127.0.0.1:5000)
to view the app interface. API endpoints are shown below, and see [examples](examples)
for a full client and example scripts to interact with your server. E.g., here
is an example:

```console
$ python3 examples/submit_job.py
```

To use authentication, you can either export your user and token to the environment, as before
(and they will be found by the client):

```bash
export FLUX_USER=$USER
export FLUX_TOKEN=123456
```
or if you cannot do this, the client can accept the username and password token at creation or
after it:

```python
# Make sure the directory with the client is in sys.path
from flux_restful_client import FluxRestfulClient

# create with username and token
cli = FluxRestfulClient(user="fluxuser", token="12345")

# Add or update after creation
cli.set_basic_auth(user="fluxuser", token="12345")
```
In addition, you can set the hostname (which defaults to localhost on port 5000):

```python
# create with username and token
cli = FluxRestfulClient('http://127.0.0.1:5000')
```

See the [examples](examples) folder for a mix of example (one with submit with auth)!

## Code Linting

We use [pre-commit](https://pre-commit.com/) to handle code linting and formatting, including:

 - black
 - isort
 - flake8

Our setup also handles line endings and ensuring that you don't add large files!

Using the tools is easy. After preparing your local environment,
you can use pre-commit as follows. Here is a manual run:

```bash
$ pre-commit run --all-files
```
```console
check for added large files..............................................Passed
check for case conflicts.................................................Passed
check docstring is first.................................................Passed
fix end of files.........................................................Passed
trim trailing whitespace.................................................Passed
mixed line ending........................................................Passed
black....................................................................Passed
isort....................................................................Passed
flake8...................................................................Passed
```

And to install as a hook (recommended so you never commit with linting flaws!)

```bash
$ pre-commit install
```


## Documentation

The documentation is provided in the `docs` folder of the repository,
and generally most content that you might want to add is under
`getting_started`. For ease of contribution, files that are likely to be
updated by contributors (e.g., mostly everything but the module generated files)
 are written in markdown. If you need to use [toctree](https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html#table-of-contents) you should not use extra newlines or spaces (see index.md files for examples). The documentation is also provided in Markdown (instead of rst or restructured syntax)
to make contribution easier for the community.

Finally, we recommend you use the same development environment also to build and work on
documentation. The reason is because we import the app to derive docstrings,
and this will require having Flux.

**NOTE** to build the documentation you will need an unathenticated flux endpoint
running. E.g., in another terminal:

```bash
$ flux start uvicorn app.main:app --host=0.0.0.0 --port=5000
```

### Install Dependencies and Build

The documentation is built using sphinx, and generally you can install
dependencies (done in devcontainer):

```console
cd docs
pip install -r requrements.txt

# Build the docs into _build/html
make html
```

### Preview Documentation

After `make html` you can enter into `_build/html` and start a local web
server to preview:

```console
$ python -m http.server 9999
```

And open your browser to `localhost:9999`

### Docstrings

To render our Python API into the docs, we keep an updated restructured
syntax in the `docs/source` folder that you can update on demand as
follows:

```console
$ ./apidoc.sh
```

This should only be required if you change any docstrings or add/remove
functions from oras-py source code.
