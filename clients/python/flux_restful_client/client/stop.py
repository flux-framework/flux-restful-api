import json

from flux_restful_client.main import get_client


def stop_service(args, parser, extra, subparser):
    cli = get_client(quiet=args.quiet, settings=args.settings_file)
    cli.settings.update_params(args.config_params)
    info = cli.stop_service()
    print(json.dumps(info, indent=4))
