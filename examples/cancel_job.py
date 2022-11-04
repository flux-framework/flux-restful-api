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
    print('Submitting job sleep 60 intending to cancel..')
    res = cli.submit(command=['sleep', 60])
    if res:
        print(json.dumps(res, indent=4))
        print('Requesting job cancel..')
        res = cli.cancel(res['id'])
        print(json.dumps(res, indent=4))

if __name__ == "__main__":
    main()