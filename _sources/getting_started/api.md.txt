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

### GET `/jobs/{uid}`

Get a job with a specific identifier.

### POST `/jobs/{uid}/cancel`

Request for a job cancellation based on identifier.

### POST `/jobs/submit`

Submit a new job, required metadata in the post is:

 - command: a string of the command to run (required)
 - runtime: maximum runtime allowed (defaults to 0, unlimited, optional)

## Nodes

### GET `/nodes`

List cluster nodes.
