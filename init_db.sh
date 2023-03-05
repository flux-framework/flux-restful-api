#!/bin/bash

# This is an example to init the database
# These credentials are just for testing - you should export your own before running.
FLUX_USER=${FLUX_USER:-fluxuser}
FLUX_TOKEN=${FLUX_USER:-12345}

python app/db/init_db.py init
# python app/db/init_db.py add-user peenut peenut
