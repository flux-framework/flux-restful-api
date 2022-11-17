#!/bin/bash

install_branch=${INSTALL_BRANCH}
install_repo=${INSTALL_REPO:-flux-framework/flux-restful-api}

# If we are given a custom branch to install, do that first
if [[ ! -z ${install_branch} ]]; then
    cd /tmp
    printf "Custom install of https://github.com:${install_repo}@${install_branch}"
    rm -rf /code
    git clone -b ${install_branch} https://github.com/${install_repo} /code
    cd /code
fi

flux start uvicorn app.main:app --host=${HOST} --port=${PORT}
