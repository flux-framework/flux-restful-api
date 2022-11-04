#!/usr/bin/env python3

import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)

from flux_restful_client import FluxRestfulClient  # noqa


def main():
    cli = FluxRestfulClient()

    # Submit the job to flux
    print("😴 Submitting job sleep 60")
    res = cli.submit(command=["sleep", 60])
    if res and "detail" not in res:
        print(json.dumps(res, indent=4))
        print("🍓 Getting job info...")
        res = cli.jobs(res["id"])
        if res:
            print(json.dumps(res, indent=4))


if __name__ == "__main__":
    main()
