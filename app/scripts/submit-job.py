#!/usr/bin/env python3

import sys

import flux
import flux.job

payload = sys.stdin.read()
fluxjob = flux.job.JobspecV1.from_yaml_stream(payload)
print(flux.job.submit_async(flux.Flux(), payload).get_id().decode("utf-8"))
