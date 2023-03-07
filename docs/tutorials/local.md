# Local Install

This tutorial will show running the Flux Restful API on an allocation where you have flux
(so you are the instance owner). This is arguably unecessary, because you have the Flux
command line client to interact with, but we show the example to demonstrate that it's
possible.

## Get an Allocation.

We want to start with an allocation so we are already running in our own Flux
instance. Let's say we ask for the allocation:

```bash
$ flux alloc -N 2

# Older versions of flux
$ flux mini alloc -N 2
```

We can then clone the flux-restful API:

```bash
git clone --depth 1 https://github.com/flux-framework/flux-restful-api
cd flux-restful-api
```

and create an environment for it:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Database

Prepare the database. Note that this can also be done with `make init`.

```bash
alembic revision --autogenerate -m "Create intital tables"
alembic upgrade head
```

Export your desired flux token and user, and create the database.

```bash
export FLUX_USER=dinosaur
export FLUX_TOKEN=dinosaur

./init_db.sh
```

## Start

And run! This can also be done by running `make` (and inspect the Makefile first
for port variables, etc):

```bash
$ flux start uvicorn app.main:app --host=0.0.0.0 --port=16798 --workers=2
```

Note that we are using a very large port number.

## Interact

At this point you'd want to shell into another terminal, and return to the same cloned
directory!  The easiest thing to do (to test quickly) is to shell into the node where
you have the allocation. E.g.,:

```bash
$ ssh corona194
```

And return to that directory. We can cd into the python client and install:

```bash
$ source env/bin/activate
$ cd clients/python
$ pip install -e .
```

### Python

We can now derive an interaction via example in the examples directory.
I like to use ipython when I'm developing or testing like this, but you
could use python or just a script. First, submit the job:


```python
from flux_restful_client.main import get_client

# You can also again export these in the environment.
cli = get_client(host="http://127.0.0.1:16798", user="dinosaur", token="dinosaur")

cli.submit(command=["whoami"])
# {'Message': 'Job submit.', 'id': 8245884223488}
```

Note the id! Let's get it back to see the result.

```
# see all jobs
res = jobs = cli.jobs()
# {'jobs': [{'id': 8245884223488}]}

# Or get the specific job
job = cli.jobs(res['id'])
```
```console
{'id': 8245884223488,
 'userid': 34633,
 'urgency': 16,
 'priority': 16,
 't_submit': 1678216131.163,
 't_depend': 1678216131.163,
 't_run': 1678216131.1762564,
 't_cleanup': 1678216131.234502,
 't_inactive': 1678216131.2362921,
 'state': 'INACTIVE',
 'name': 'whoami',
 'ntasks': 1,
 'ncores': 1,
 'duration': 0.0,
 'nnodes': 1,
 'ranks': '0',
 'nodelist': 'corona194',
 'success': True,
 'exception_occurred': False,
 'result': 'COMPLETED',
 'expiration': 4831816131.0,
 'waitstatus': 0,
 'returncode': 0,
 'runtime': 0.05824565887451172,
 'exception': {'occurred': False, 'severity': '', 'type': '', 'note': ''}}
```

And finally, get the log:

```bash
out = cli.output()
# {'Output': ['sochat1\n']}
```

And that's it! You've successfully used the flux restful API in single user
mode, of course running as yourself.

### Command Line

Now let's produce the same thing from the command line! This time we will export
our credentials and the host for the client to find:

```bash
export FLUX_USER=dinosaur
export FLUX_TOKEN=dinosaur
export FLUX_RESTFUL_HOST=http://127.0.0.1:16798
```

And then submit the job:

```bash
$ flux-restful-cli submit whoami
```
```console
{
    "Message": "Job submit.",
    "id": 1944496111616
}
```
```console
{
    "id": 1944496111616,
    "userid": 34633,
    "urgency": 16,
    "priority": 16,
    "t_submit": 1678217369.1978858,
    "t_depend": 1678217369.1978858,
    "t_run": 1678217369.211171,
    "t_cleanup": 1678217369.2724185,
    "t_inactive": 1678217369.2742176,
    "state": "INACTIVE",
    "name": "whoami",
    "ntasks": 1,
    "ncores": 1,
    "duration": 0.0,
    "nnodes": 1,
    "ranks": "0",
    "nodelist": "corona194",
    "success": true,
    "exception_occurred": false,
    "result": "COMPLETED",
    "expiration": 4831817369.0,
    "waitstatus": 0,
    "returncode": 0,
    "runtime": 0.06124758720397949,
    "exception": {
        "occurred": false,
        "severity": "",
        "type": "",
        "note": ""
    }
}
```

Or list jobs...

```bash
$ flux-restful-cli list-jobs
```
```console
{
    "jobs": [
        {
            "id": 1944496111616
        }
    ]
}
```
or nodes..

```bash
$ flux-restful-cli list-nodes
```
```console
{
    "nodes": [
        "corona194"
    ]
}

```

Or finally, get the output!
