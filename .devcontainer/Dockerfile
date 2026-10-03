FROM fluxrm/flux-sched:jammy

LABEL maintainer="Vanessasaurus <@vsoch>"

# Pip not provided in this version
USER root
RUN apt-get update && apt-get install -y python3-venv systemctl python3-pip
COPY ./requirements.txt /requirements.txt
COPY ./.github/dev-requirements.txt /dev-requirements.txt
COPY ./docs/requirements.txt /docs-requirements.txt

EXPOSE 5000
ENV PYTHONPATH=/usr/lib/flux/python3.10

# For easier Python development.
RUN python3 -m pip install IPython && \
    python3 -m pip install -r /requirements.txt && \
    python3 -m pip install -r /dev-requirements.txt && \
    python3 -m pip install -r /docs-requirements.txt

RUN mkdir -p /run/flux /var/lib/flux mkdir /etc/flux/system/cron.d /mnt/curve && \
    flux keygen /mnt/curve/curve.cert && \
    # These need to be owned by flux
    chown -R fluxuser /run/flux /var/lib/flux /mnt/curve && \
    # flux-imp needs setuid permission
    chmod u+s /usr/libexec/flux/flux-imp

ENV PATH=/env/bin:${PATH}
