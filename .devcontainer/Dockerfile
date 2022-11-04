FROM fluxrm/flux-sched:focal

LABEL maintainer="Vanessasaurus <@vsoch>"

# Pip not provided in this version
USER root
RUN apt-get update
COPY ./requirements.txt /requirements.txt
COPY ./dev-requirements.txt /dev-requirements.txt

EXPOSE 5000
ENV PYTHONPATH=/usr/lib/flux/python3.8

# For easier Python development.
RUN python3 -m pip install IPython && \
    python3 -m pip install -r /requirements.txt && \
    python3 -m pip install -r /dev-requirements.txt
