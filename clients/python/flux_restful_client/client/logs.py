import json

from flux_restful_client.main import get_client


def main(args, parser, extra, subparser):
    cli = get_client(quiet=args.quiet, settings=args.settings_file)

    # Update config settings on the fly
    cli.settings.update_params(args.config_params)
    logs = cli.output(jobid=args.jobid)
    if "Output" in logs:
        for line in logs["Output"]:
            print(line)
    else:
        print(json.dumps(logs, indent=4))
