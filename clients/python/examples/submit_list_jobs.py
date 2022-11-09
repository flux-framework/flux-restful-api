#!/usr/bin/env python3

import json

from flux_restful_client.main import get_client


def main():
    cli = get_client

    # Submit the job to flux
    print("Submitting 3 jobs to sleep!")
    for time in [10, 20, 30]:
        cli.submit(command=["sleep", time])
    res = cli.jobs()
    if res:
        print(json.dumps(res, indent=4))


if __name__ == "__main__":
    main()
