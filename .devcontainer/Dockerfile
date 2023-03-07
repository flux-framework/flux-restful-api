FROM ghcr.io/rse-ops/pokemon:app-latest

LABEL maintainer="Vanessasaurus <@vsoch>"

# Pip not provided in this version
USER root
RUN apt-get update && apt-get install -y python3-venv systemctl
COPY ./requirements.txt /requirements.txt
COPY ./.github/dev-requirements.txt /dev-requirements.txt
COPY ./docs/requirements.txt /docs-requirements.txt

EXPOSE 5000
ENV PYTHONPATH=/usr/lib/flux/python3.8

# For easier Python development.
RUN python3 -m pip install IPython && \
    python3 -m pip install -r /requirements.txt && \
    python3 -m pip install -r /dev-requirements.txt && \
    python3 -m pip install -r /docs-requirements.txt

RUN python3 -m venv /env && \
    . /env/bin/activate && \
    pip install -r /requirements.txt && \
    pip install -r /dev-requirements.txt && \
    pip install -r /docs-requirements.txt && \
    # Only for development - don't add this to a production container
    sudo useradd -m -p $(openssl passwd '12345') "flux"

RUN mkdir -p /run/flux /var/lib/flux mkdir /etc/flux/system/cron.d /mnt/curve && \
    flux keygen /mnt/curve/curve.cert && \
    # These need to be owned by flux
    chown -R flux /run/flux /var/lib/flux /mnt/curve && \
    # flux-imp needs setuid permission
    chmod u+s /usr/libexec/flux/flux-imp

ENV PATH=/env/bin:${PATH}
