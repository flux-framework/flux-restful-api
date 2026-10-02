#!/bin/bash

# This is an example to init the database
# These credentials are just for testing - you should export your own before running.
FLUX_USER=${FLUX_USER:-fluxuser}
FLUX_TOKEN=${FLUX_USER:-12345}

flux-restful init || flux-restful init
# flux-restful add-user peenut peenut
