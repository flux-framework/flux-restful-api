FROM fluxrm/flux-sched:focal

# docker build -t ghcr.io/flux-framework/flux-restful-api .

# This must be set to work (username / token set won't trigger it alone)
ARG use_auth
ARG user="fluxuser"
ARG token="12345"
ARG port="5000"
ARG host="0.0.0.0"
ARG workers="1"
LABEL maintainer="Vanessasaurus <@vsoch>"

ENV FLUX_USER=${user}
ENV FLUX_TOKEN=${token}
ENV FLUX_REQUIRE_AUTH=${use_auth}
ENV PORT=${port}
ENV HOST=${host}
ENV WORKERS=${workers}

USER root
RUN apt-get update
COPY ./requirements.txt /requirements.txt

EXPOSE ${port}
ENV PYTHONPATH=/usr/lib/flux/python3.8:/code

# For easier Python development, and install time for timed commands
RUN python3 -m pip install -r /requirements.txt && \
    apt-get update && apt-get install -y time && \
    apt-get clean && \
    apt-get autoremove && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code
COPY . /code
ENTRYPOINT ["/code/entrypoint.sh"]
