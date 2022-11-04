#!/usr/bin/env python3

import os 
import sys 
import json

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)

from flux_restful_client import FluxRestfulClient

def main():
    cli = FluxRestfulClient() 
    
    # Submit the job to flux
    print('Submitting 3 jobs to sleep!')
    for time in [10, 20, 30]:
        cli.submit(command=['sleep', time])
    res = cli.jobs()
    if res:
        print(json.dumps(res, indent=4))

if __name__ == "__main__":
    main()