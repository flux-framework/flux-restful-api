import json

from flux_restful_client.logger import logger
from flux_restful_client.main import get_client


def main(args, parser, extra, subparser):
    cli = get_client(quiet=args.quiet, settings=args.settings_file)

    if not extra:
        logger.exit("Please include the command that you want to submit!")

    # Update config settings on the fly
    cli.settings.update_params(args.config_params)

    # The command is the "extra"
    kwargs = {"command": extra}
    for arg in [
        "num_tasks",
        "cores_per_task",
        "gpus_per_task",
        "num_nodes",
        "exclusive",
        "workdir",
    ]:
        if hasattr(args, arg) and getattr(args, arg, None) is not None:
            kwargs[arg] = getattr(args, arg)

    res = cli.submit(**kwargs)
    print(json.dumps(res, indent=4))
