# User Guide

Welcome to the Flux RESTful API user guide! If you come here, we are assuming
that you have a deployment available to use to interact with. If you need
to deploy your own API, see the [Developer Documentation](https://flux-framework.org/flux-restful-api/getting_started/developer-guide.html).
We provide [clients](https://github.com/flux-framework/flux-restful-api/tree/main/clients) to interact with
a running server, each described below, along with a quick container tutorial.
The Python client is also included in our [Tutorials](https://flux-framework.org/flux-restful-api/auto_examples/index.html).

## Environment

You should either have a Flux user and token from the server you created, or provided to you
by an administrator. Currently Flux RESTFul API only supports the single user case,
however this could be extended for other use cases (please [reach out](https://github.com/flux-framework/flux-restful-api/issues)
to talk about design).

```bash
$ export FLUX_USER=fluxuser
$ export FLUX_TOKEN=12345
```

You really should only be interacting with a server that doesn't require authentication if you are a developer.
From here, continue reading the user guide for different language clients,
or see our Python [examples](https://github.com/flux-framework/flux-restful-api/tree/main/clients/python/examples) folder.

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
a script. Here are examples:

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

### Stop Service

Finally, to stop your service (this is a special functionality intended for the operator!)

```bash
$ flux-restful-cli stop-service
```
(this isn't tested yet with the operator - might have a bug or two!)


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
