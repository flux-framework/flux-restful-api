# API

The following is the spec for the Flux Python RESTful API provided here:

## Service

### POST `/service/stop`

Request to stop the server from running. This is intended for applications like
the Flux Operator that need programmatic ability to end the flux start command
and thus exit the job and bring down the mini-cluster.

## Jobs

### GET `/jobs`

List jobs owned by the flux executor (the current user).

### POST `/jobs/submit`

Submit a new job

#### Payload

**Required** parameters in the post are:

 - command (string or list): a string of the command to run (required)
 - runtime (int): maximum runtime allowed (defaults to 0, unlimited, optional)

**Optional** parameters include:

- workdir (str): a working directory for the job. Defaults to "None" which is unset.
- envars (dict): A set of key, value pairs (dict) of environment variables to add
- num_tasks (int): Number of tasks (defaults to 1)
- cores_per_task (int): Number of cores per task (default to 1)
- gpus_per_task (int): Number of gpus per task (defaults to None)
- num_nodes (int): Number of nodes (defaults to None)
- exclusive (bool): is the job exclusive? (defaults to False)

### GET `/jobs/{uid}`

Get a job with a specific identifier.

### POST `/jobs/{uid}/cancel`

Request for a job cancellation based on identifier.

### GET `/jobs/{uid}/output`

Get lines of job output.

## Nodes

### GET `/nodes`

List cluster nodes.
