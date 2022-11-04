#!/usr/bin/env python3

import os 
import sys 
import json

# This is the same example as the submit_job.py, but with authentication 
# added. You should start the server with the following environment
# variables exported:
# FLUX_USER=fluxuser
# FLUX_TOKEN=12345
# FLUX_REQUIRE_AUTH=true

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)

from flux_restful_client import FluxRestfulClient

def main():
    cli = FluxRestfulClient() 
    
    # Submit the job to flux
    print('😴 Submitting job sleep 60')
    res = cli.submit(command=['sleep', 60])
    if res:
        print(json.dumps(res, indent=4))
    print('🍓 Getting job info...')
    res = cli.jobs(res['id'])
    if res:
        print(json.dumps(res, indent=4))
  
if __name__ == "__main__":
    main()