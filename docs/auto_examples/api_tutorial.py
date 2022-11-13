# -*- coding: utf-8 -*-
"""
Introductory example - using the API
====================================

This small tutorial walks through the basics of using an API.
The most basic thing to do is submit a job to the API,
list, get statuses, cancel. We can use our example client for this.
"""

import json
import os
import sys

import matplotlib.pyplot as plt
from flux_restful_client.main import get_client

# This is expected to be rendered from docs root
here = os.path.dirname(os.path.abspath(os.getcwd()))

# This is here for the nice thumbnail :)
image = plt.imread(os.path.join(here, "images", "logo.png"))
fig = plt.imshow(image)
plt.axis("off")
plt.show()

#%%
# Here we instantiate a client. If you need authentication, this can optionally take
# a user and token, or also derive from the FLUX_USER and FLUX_TOKEN in the
# environment.

cli = get_client()

#%%
# Let's list the nodes in our cluster!
print("Listing nodes")
res = cli.list_nodes()
if res:
    print(json.dumps(res, indent=4))


#%%
# Now let's submit a job to Flux.

print("😴 Submitting job sleep 60")
res = cli.submit(command=["sleep", 60])

# This is an indication something went wrong - detail has an error.
if res and "detail" in res:
    print(res["detail"])
    sys.exit()

#%%
# To require auth, the server should be startup with these variables
# in the environment (and the first two found by the client here)
# variables exported:
# FLUX_USER=fluxuser
# FLUX_TOKEN=12345
# FLUX_REQUIRE_AUTH=true

#%%
# And finally, let's get job info.
print("🍓 Getting job info...")
res = cli.jobs(res["id"])
if res:
    print(json.dumps(res, indent=4))


#%%
# And job logs
# This will be added to the client
print("😴 Submitting job to echo pancakes 🥞🥞🥞")
res = cli.submit(command="echo pancakes are really just morning cakes.")
res = cli.output(res["id"])
if res:
    print(json.dumps(res, indent=4))


#%%
# Now let's submit three jobs in unison so we can list them back!
# Submit the job to flux
print("Submitting 3 jobs to sleep!")
for time in [10, 20, 30]:
    cli.submit(command=["sleep", time])
res = cli.jobs()
if res:
    print(json.dumps(res, indent=4))

#%%
# And this is how to search (with a start, length, or query)
print("🌓 Querying jobs!")
res = cli.search("sleep", start=1, length=2)
if res:
    print(json.dumps(res, indent=4))


#%%
# Finally, let's submit and cancel a job
print("Submitting job sleep 60 intending to cancel..")
res = cli.submit(command=["sleep", 60])
if res:
    print(json.dumps(res, indent=4))
    print("Requesting job cancel..")
    res = cli.cancel(res["id"])
    print(json.dumps(res, indent=4))

#%%
# And this would be how you stop your cluster service
print("Stopping the service...")
# res = cli.stop_service()
