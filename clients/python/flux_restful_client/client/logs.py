import json

from flux_restful_client.main import get_client


def main(args, parser, extra, subparser):
    cli = get_client(quiet=args.quiet, settings=args.settings_file)

    # Update config settings on the fly
    cli.settings.update_params(args.config_params)
    if args.stream:
        for line in cli.stream_output(jobid=args.jobid, stream=args.stream):
            print(line.strip())
    else:
        logs = cli.output(jobid=args.jobid, stream=args.stream)
        if "Output" in logs:
            for line in logs["Output"]:
                # Ensure we only have one newline!
                print(line.strip())
        else:
            print(json.dumps(logs, indent=4))
