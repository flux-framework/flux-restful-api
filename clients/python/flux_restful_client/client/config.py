import sys

import flux_restful_client.defaults as defaults
from flux_restful_client.logger import logger
from flux_restful_client.main import get_client


def main(args, parser, extra, subparser):

    # If nothing provided, show help
    if not args.params:
        print(subparser.format_help())
        sys.exit(0)

    # The first "param" is either set of get
    command = args.params.pop(0)

    # If the user wants the central config file
    if args.central:
        args.settings_file = defaults.default_settings_file

    validate = True if not command == "edit" else False
    cli = get_client(
        quiet=args.quiet, settings_file=args.settings_file, validate=validate
    )

    # Update config settings on the fly
    cli.settings.update_params(args.config_params)

    # For each new setting, update and save!
    if command == "inituser":
        return cli.settings.inituser()
    if command == "edit":
        return cli.settings.edit()

    if command in ["set", "add", "remove"]:
        cli.settings.update_param(command, args.params)

        # Save settings
        cli.settings.save()

    # For each get request, print the param pair
    elif command == "get":
        for key in args.params:
            value = cli.settings.get(key)
            value = "is unset" if value is None else value
            logger.info("%s %s" % (key.ljust(30), value))

    else:
        logger.error("%s is not a recognized command." % command)
