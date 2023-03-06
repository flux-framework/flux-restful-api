#!/usr/bin/env python3

# See https://github.com/flux-framework/flux-core/blob/master/t/t2404-job-exec-multiuser.t#L48
# for an example of using this. This should be run with flux python, as done in library/flux.py
import sys

from flux.security import SecurityContext

if len(sys.argv) < 2:
    print("Usage: {0} USERID".format(sys.argv[0]))
    sys.exit(1)

userid = int(sys.argv[1])
ctx = SecurityContext()
payload = sys.stdin.read()

print(ctx.sign_wrap_as(userid, payload, mech_type="none").decode("utf-8"))
