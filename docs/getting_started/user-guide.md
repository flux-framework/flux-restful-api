# User Guide

Welcome to the Flux RESTful API user guide! If you come here, we are assuming
that you have a deployment available to use to interact with. If you need
to deploy your own API, see the [Developer Documentation](https://flux-framework.org/flux-restful-api/getting_started/developer-guide.html).
We provide [clients](https://github.com/flux-framework/flux-restful-api/tree/main/clients) to interact with
a running server, each described below, along with a quick container tutorial.
The Python client is also included in our [Tutorials](https://flux-framework.org/flux-restful-api/auto_examples/index.html).

## How does it work?

### Modes

There are two modes of interaction:

 - **single-user mode**: assumes you are running an instance as the flux user, and submitting jobs as that user.
 - **multi-user mode**: requires authentication via the RESTful API with an encoded payload to request expiring tokens. When authentication is successful, the
   job is run as the same user on the system on behalf of the flux user.

To control the user mode, you can export it to the environment where you are running the server:

```bash
# This is the default
export FLUX_SERVER_MODE=single-user

# This will have the flux user attempt to sign the payload with sudo
export FLUX_SERVER_MODE=multi-user
```

Note that the majority of our use cases use single-user mode, so you can expect more bugs / work to be
done with multi-user.

### Authentication

If you choose to deploy without authentication, this is a ⚠️ proceed at your own risk ⚠️ sort of deal.
We call this the "single-user" case, and it means that you are submitting jobs as the instance owner,
typically a user named "flux." If it's just you that owns the cluster, or a small group of trusted friends,
this is probably OK. When you enable authentication, the following happens:

 - A server secret that you export via `FLUX_SECREY_KEY` is used to encode payloads. You'll need to provide this to users.
 - The server is created adding users with names and passwords, so every user known to Flux Restful is known to the server.
   - Passwords are hashed
   - We don't currently check authentication here with PAM (but we could).
 - A user making a request provided an encoded payload (first) with the encoded username and password
 - The server decodes the payload, authenticates, and (given a valid username and password) generates an expiring token.
 - The user adds the token header to subsequent requests.

To require this authentication, we set a few environment variables to turn it on and define credentials
and a secret (e.g., a driver that is running the API might randomly generate these accounts and secret) and then all interactions
with the API or interface require authenticating. As an example, the Flux Operator will make both the server user
accounts and the Flux Restful database accounts when you spin up a MiniCluster.

#### Web Interface Basic Authentication

In the case of the web interface (which does not necessarily need to be exposed, e.g., the Flux Operator requires a port forward)
we fall back to basic auth, and the user needs to enter a username and password.

#### API OAuth2 Style Authentication

In the case of the API, we taken an OAuth2 based approach, where a request will originally
return with a 401 status and the "www-authenticate" header, and the calling client needs to then prepare an encoded
payload to request a token. A successful receipt of the payload will return the token,
which can be added to an Authorization header for subsequent requests (up until it expires).

You largely don't need to worry about the complexity of the above because the SDKs will
handle these interactions for you, given that you've provided some credentials and secret key.
If you are using the Flux Operator, you largely don't need to do anything, as it will
generate and provide both.

## What does this user-guide include?

This user-guide assumes you are a user of the flux restful API, meaning you are either
running it alongside a production Flux cluster, or it's running already in another
context and you have been given credentials to access it. If you want to learn about how
to setup the API itself, see the [developer documentation](developer-guide.md).


## Environment

Whether you are in single- or multi- user mode, you will need a username and token to
interact with the server. In single-user mode this will be the flux superuser credentials
that the server was created with. In multi-user mode this will be your username and password,
along with a secret key to encode paylods for the token. E.g.,

```bash
$ export FLUX_USER=fluxuser
$ export FLUX_TOKEN=12345
$ export FLUX_SECRET_KEY=notsecrethoo
```

From here, continue reading the user guide for different language clients,
or see our Python [examples](https://github.com/flux-framework/flux-restful-api/tree/main/clients/python/examples) folder
for snippet examples, or the [tutorials](../tutorials/index.md) for more complex setups.

## Python

### Installation

You likely want this installed in a virtual environment:

```bash
$ python -m venv env
$ source env/bin/activate
```

You can install the client from pip:

```bash
$ pip install flux-restful-client
```

Or from the repository directly:

```bash
$ git clone https://github.com/flux-framework/flux-restful-api
$ cd flux-restful-api/clients/python
# Install to your Python install
$ pip install .

# Development version using the code here
$ pip install -e .
```

### Command Line Client

Although most of you will want to interact with the client in Python, we also install
a simple command line client to let you "one off" a quick command without needing to write
a script. The same environment variables would be needed to be exported. Here are examples:

#### Submit

Submit usage is as follows:

```bash
$ flux-restful-cli submit --help
```
```console
usage: flux-restful-cli submit [-h] [--workdir WORKDIR] [--num_tasks NUM_TASKS] [--cores_per_task CORES_PER_TASK] [--gpus_per_task GPUS_PER_TASK] [--num_nodes NUM_NODES] [--exclusive]

submit a job via the flux restful client

optional arguments:
  -h, --help            show this help message and exit
  --workdir WORKDIR     working directory for the job to run
  --num_tasks NUM_TASKS
                        number of tasks for the job.
  --cores_per_task CORES_PER_TASK
                        number of cores per task for the job.
  --gpus_per_task GPUS_PER_TASK
                        number of gpus per task for the job.
  --num_nodes NUM_NODES
                        number of nodes for the job.
  --exclusive           ask for exclusive nodes for the job.
  --is_launcher         indicate the command is for a launcher (e.g., nextflow, snakemake)
  --env ENVARS          "key=value pairs to provide to the job in the environment (add as many as you need)
                        flux-restful-cli --env PIPELINE_VAR=one ...
                        flux-restful-cli --env SUPERHERO=batman --env SUPERHERO_NAME=manbat ...
```

The only requirement is the command, which you can add to the end of the submit request.
Here is submitting a basic job to sleep.

```bash
$ flux-restful-cli submit sleep 60
```
```console
{
    "Message": "Job submit.",
    "id": 12402053611520
}
```

### Cancel

While we can't get confirmation of cancel, we can request it.

```bash
$ flux-restful-cli cancel --help
```
```console
usage: flux-restful-cli cancel [-h] jobid

cancel a job

positional arguments:
  jobid       The jobid to interact with.

optional arguments:
  -h, --help  show this help message and exit
```

Here is an example to cancel the job we just submit!

```bash
$ flux-restful-cli cancel 12402053611520
```
```console
{
    "Message": "Job is requested to cancel."
}
```

### Job Info

Get information on a specific job:

```bash
$ flux-restful-cli info 12402053611520
```
```console
{
    "job": {
        "id": 12402053611520,
        "userid": 1234,
        "urgency": 16,
        "priority": 16,
        "t_submit": 1667941663.3324268,
        "t_depend": 1667941663.3324268,
        "t_run": 1667941663.3549669,
        "t_cleanup": 1667941723.4129763,
        "t_inactive": 1667941723.4203393,
        "state": 64,
        "name": "sleep",
        "ntasks": 1,
        "nnodes": 1,
        "ranks": "3",
        "nodelist": "flux-sample-3",
        "success": true,
        "exception_occurred": false,
        "result": 1,
        "expiration": 1668546463.0,
        "annotations": {
            "sched": {
                "queue": "default"
            }
        },
        "waitstatus": 0
    }
}
```

### Logs

To see output for a job, there are two options. You can ask for all logs (blocking, will return when job is done):

```bash
$ flux-restful-cli logs 12402053611520
```
```console
# flux-restful-cli logs 244509770252288
pancakes 🥞🥞🥞🥞🥞
```

Or you can ask to stream:

```bash
$ flux-restful-cli logs --stream 12402053611520
```

If you get a message that the output doesn't exist, it usually means your job didn't have output (e.g., sleep),
or the job was not found.

### List Jobs

You can list jobs:

```bash
$ flux-restful-cli list-jobs
```
```console
{
    "jobs": [
        {
            "id": 22883485089792
        },
        {
            "id": 12402053611520
        }
    ]
}
```

### List Nodes

Or you can list node available (these are running inside a Flux Operator!)

```bash
$ flux-restful-cli list-nodes
```
```console
{
    "nodes": [
        "flux-sample-3",
        "flux-sample-0",
        "flux-sample-2",
        "flux-sample-1"
    ]
}
```

### Shell

Or get an interactive shell to play with the client from within Python (discussed next)


```bash
$ flux-restful-cli shell
```
```python
In [2]: client
Out[2]: [flux-restful-client]

In [3]: client.submit
Out[3]: <bound method FluxRestfulClient.submit of [flux-restful-client]>
```

### Config

There are many ways to interact with your settings config (e.g., `inituser` creates one in your user home to customize):

```bash
$ flux-restful-cli config --help
```
```console
usage: flux-restful-cli config [-h] [--central] [params ...]

update configuration settings. Use set or get to see or set information.

positional arguments:
  params      Set or get a config value, edit the config, add or remove a list variable, or create a user-specific config.
              flux-restful-cli config set key value
              flux-restful-cli config set key:subkey value
              flux-restful-cli config get key
              flux-restful-cli edit
              flux-restful-cli config inituser

optional arguments:
  -h, --help  show this help message and exit
  --central   make edits to the central config file.
```

Here is an example to edit:

```bash
$ flux-restful-cli config edit
```


### Within Python

See our [tutorial](https://flux-framework.org/flux-restful-api/auto_examples/api_tutorial.html#sphx-glr-auto-examples-api-tutorial-py) for this complete
example!

```python
# Make sure the directory with the client is in sys.path
from flux_restful_client import get_client

# create with username and token
cli = get_client(user="fluxuser", token="12345")

# Add or update after creation
cli.set_basic_auth(user="fluxuser", token="12345")
```

In addition, you can set the hostname (which defaults to localhost on port 5000):

```python
# create with username and token
cli = get_client('http://127.0.0.1:5000')
```

See the [examples](https://github.com/flux-framework/flux-restful-api/tree/main/client/python/examples) folder for a mix of example (one with submit with auth)!

## Go

Coming soon (or sooner upon request)!
