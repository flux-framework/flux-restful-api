#!/usr/bin/env python3

import sys

import flux
import flux.job

payload = sys.stdin.read()
fluxjob = flux.job.JobspecV1.from_yaml_stream(payload)
job = flux.job.submit_async(flux.Flux(), payload)
print(job.get_id())
