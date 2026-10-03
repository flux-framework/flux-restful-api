#!/bin/bash

FLUX_SECRET_KEY=${FLUX_SECRET_KEY:-notsecrethoo}

# The database lives in the working directory
cd /code

# prepare the database - we always start from scratch, it's ephemeral.
# The CLI is invoked as a module so this does not depend on where pip put
# the flux-restful console script.
python3 -m flux_restful.cli init
# python3 -m flux_restful.cli add-user myuser mypass

# Access tokens are signed with a server-only key that every uvicorn worker
# must share. Generate one for this container if not provided.
FLUX_TOKEN_SIGNING_KEY=${FLUX_TOKEN_SIGNING_KEY:-$(python3 -c 'import secrets; print(secrets.token_hex(32))')}

export FLUX_SECRET_KEY
export FLUX_TOKEN_SIGNING_KEY
export FLUX_USER
export FLUX_TOKEN

# And start the webserver
flux start python3 -m flux_restful.cli serve --host=${HOST} --port=${PORT} --workers=${WORKERS}
