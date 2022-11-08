#!/usr/bin/env python3

import json

from flux_restful_client.main import get_client


def main():
    cli = get_client()

    # Submit the job to flux
    print("Listing nodes")
    res = cli.list_nodes()
    if res:
        print(json.dumps(res, indent=4))


if __name__ == "__main__":
    main()
