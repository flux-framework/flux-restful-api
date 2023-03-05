#!/bin/bash

install_branch=${INSTALL_BRANCH}
install_repo=${INSTALL_REPO:-flux-framework/flux-restful-api}
FLUX_SECRET_KEY=${FLUX_SECRET_KEY:-notsecrethoo}

# If we are given a custom branch to install, do that first
if [[ ! -z ${install_branch} ]]; then
    cd /tmp
    printf "Custom install of https://github.com:${install_repo}@${install_branch}"
    rm -rf /code
    git clone -b ${install_branch} https://github.com/${install_repo} /code
fi

# We always need to start in this PWD
cd /code

# prepare the database - we always start from scratch, it's ephemeral
alembic revision --autogenerate -m "Create intital tables"
alembic upgrade head
python3 app/db/init_db.py init
# python3 app/db/init_db.py add-user myuser mypass

export FLUX_SECRET_KEY
export FLUX_USER
export FLUX_TOKEN

# And start the webserver
flux start uvicorn app.main:app --host=${HOST} --port=${PORT} --workers=${WORKERS}
