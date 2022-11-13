# API

The following is the spec for the Flux Python RESTful API provided here.
Generally, API endpoints are versioned (e.g., start with v1) and views
do not.

## Service

### POST `/v1/service/stop`

Request to stop the server from running. This is intended for applications like
the Flux Operator that need programmatic ability to end the flux start command
and thus exit the job and bring down the mini-cluster.

## Jobs

### GET `/v1/jobs`

List jobs owned by the flux executor (the current user).
By default, this returns a simple listing with "jobs" -> a list of dict with ids.

#### Payload

**Optional** parameters in the get are:

- details (bool): provide details as True if you want to get complete metadata for the job
- listing (bool): provide listing as True if you want to get details in a list
- limit (int): provide a maximum number of jobs to retrieve (defaults to all if not provided)

### GET '/v1/jobs/search'

A custom search endpoint to query for jobs. It is used internally by the site to
render data tables and similar.

**Optional** parameters:

- start: a number to start at, must be <= the length of total jobs
- length: a length to stop at, after the start is applied (if applicable)
- query: a string to search all attributes for

**Returns** parameters:

 - data: the list of jobs
 - recordsTotal: the total number of jobs available
 - recordsFiltered: the total after fitlering by the query, length, start
 - draw: an integer used by Jquery Datatables

### POST `/v1/jobs/submit`

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

### GET `/v1/jobs/{uid}`

Get a job with a specific identifier.

### POST `/v1/jobs/{uid}/cancel`

Request for a job cancellation based on identifier.

### GET `/v1/jobs/{uid}/output`

Get lines of job output.

## Nodes

### GET `/v1/nodes`

List cluster nodes.
