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
    print('Listing nodes')
    res = cli.list_nodes()
    if res:
        print(json.dumps(res, indent=4))

if __name__ == "__main__":
    main()