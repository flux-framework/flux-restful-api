FROM fluxrm/flux-sched:focal

# docker build -t ghcr.io/flux-framework/flux-restful-api .

# This must be set to work (username / token set won't trigger it alone)
ARG use_auth
LABEL maintainer="Vanessasaurus <@vsoch>"

ENV FLUX_USER=${user:-fluxuser}
ENV FLUX_TOKEN=${token:-12345}
ENV FLUX_REQUIRE_AUTH=${use_auth}
ENV PORT=${port:-5000}
ENV HOST=${host:-0.0.0.0}
ENV WORKERS=${workers:-1}

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
