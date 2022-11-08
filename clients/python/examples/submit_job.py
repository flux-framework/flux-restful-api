#!/usr/bin/env python3

import json

from flux_restful_client.main import get_client


def main():
    cli = get_client()

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
