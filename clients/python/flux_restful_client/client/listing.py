import json

from flux_restful_client.main import get_client


def list_jobs(args, parser, extra, subparser):
    cli = get_client(quiet=args.quiet, settings=args.settings_file)

    # Update config settings on the fly
    cli.settings.update_params(args.config_params)
    res = cli.jobs()
    print(json.dumps(res, indent=4))


def list_nodes(args, parser, extra, subparser):
    cli = get_client(quiet=args.quiet, settings=args.settings_file)

    # Update config settings on the fly
    cli.settings.update_params(args.config_params)
    res = cli.list_nodes()
    print(json.dumps(res, indent=4))
