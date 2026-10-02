#!/usr/bin/env python3

# NOT USED BY THE SERVER. Kept as a reference for how flux-security wraps a
# payload as another userid, which only works with the "none" signing
# mechanism used in flux-core's tests (see t2404-job-exec-multiuser.t). With
# munge, the credential is stamped with the real uid of the calling process,
# so a server cannot sign a jobspec on another user's behalf. That is why
# multi-user submission instead becomes the user (see app/library/runas.py)
# and lets that user's own flux python sign and submit the jobspec.
import sys

from flux.security import SecurityContext

if len(sys.argv) < 2:
    print("Usage: {0} USERID".format(sys.argv[0]))
    sys.exit(1)

userid = int(sys.argv[1])
ctx = SecurityContext()
payload = sys.stdin.read()

print(ctx.sign_wrap_as(userid, payload, mech_type="munge").decode("utf-8"))
