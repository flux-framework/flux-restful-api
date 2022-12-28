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

USER root
RUN apt-get update
COPY ./requirements.txt /requirements.txt

EXPOSE ${port}
ENV PYTHONPATH=/usr/lib/flux/python3.8:/code

# For easier Python development.
RUN python3 -m pip install -r /requirements.txt

WORKDIR /code
COPY . /code
ENV FLUX_USER=${user}
ENV FLUX_TOKEN=${token}
ENV FLUX_REQUIRE_AUTH=${use_auth}
ENV PORT=${port}
ENV HOST=${host}
ENV WORKERS=${workers}
ENTRYPOINT ["/code/entrypoint.sh"]
