#!/usr/bin/env python

import argparse
import os
import sys

import flux_restful_client
import flux_restful_client.main.schemas as schemas
from flux_restful_client.logger import setup_logger


def add_submit_arguments(command):
    """
    Derive the command for argparse directly from the schema
    """
    # All all options (based on type) except for command, which comes in "extra"
    for name, attrs in schemas.submit_properties.items():
        if name == "command":
            continue
        typ = attrs.get("type")

        # This is currently just envars, we will add separately as append args.
        if not typ and "oneOf" in attrs:
            continue

        default_type = str
        action = None

        # It's either a string...
        if typ == "number" or "number" in typ:
            default_type = int
        elif typ == "boolean" or "boolean" in typ:
            default_type = bool
            # Assume default is always false for now
            action = "store_true"

        if default_type == bool:
            command.add_argument(
                f"--{name}",
                help=attrs.get("description") or f"The --{name} flag.",
                action=action,
            )
        else:
            command.add_argument(
                f"--{name}",
                help=attrs.get("description") or f"The --{name} flag.",
                type=default_type,
            )


def get_parser():
    parser = argparse.ArgumentParser(
        description="😴 Flux Restful Client Python",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Global Variables
    parser.add_argument(
        "--debug",
        dest="debug",
        help="use verbose logging to debug.",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--quiet",
        dest="quiet",
        help="suppress additional output.",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--version",
        dest="version",
        help="show software version.",
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--settings-file",
        dest="settings_file",
        help="custom path to settings file.",
    )

    # On the fly updates to config params
    parser.add_argument(
        "-c",
        dest="config_params",
        help=""""customize a config value on the fly to ADD/SET/REMOVE for a command
flux-restful-cli -c set:key:value <command> <args>
flux-restful-cli -c add:listkey:value <command> <args>
flux-restful-cli -c rm:listkey:value""",
        action="append",
    )

    subparsers = parser.add_subparsers(
        help="actions",
        title="actions",
        description="actions",
        dest="command",
    )

    # print version and exit
    subparsers.add_parser("version", description="show software version")

    # Submit a job (all extra is the command)
    submit = subparsers.add_parser(
        "submit",
        description="submit a job via the flux restful client",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_submit_arguments(submit)
    submit.add_argument(
        "--env",
        dest="envars",
        help=""""key=value pairs to provide to the job in the environment (add as many as you need)
flux-restful-cli --env PIPELINE_VAR=one ...
flux-restful-cli --env SUPERHERO=batman --env SUPERHERO_NAME=manbat ...""",
        action="append",
    )

    # Local shell with client loaded
    shell = subparsers.add_parser(
        "shell",
        description="shell into a Python session with a client.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    shell.add_argument(
        "--interpreter",
        "-i",
        dest="interpreter",
        help="python interpreter",
        choices=["ipython", "python", "bpython"],
        default="ipython",
    )

    config = subparsers.add_parser(
        "config",
        description="update configuration settings. Use set or get to see or set information.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    config.add_argument(
        "--central",
        dest="central",
        help="make edits to the central config file.",
        default=False,
        action="store_true",
    )

    config.add_argument(
        "params",
        nargs="*",
        help="""Set or get a config value, edit the config, add or remove a list variable, or create a user-specific config.
flux-restful-cli config set key value
flux-restful-cli config set key:subkey value
flux-restful-cli config get key
flux-restful-cli edit
flux-restful-cli config inituser""",
        type=str,
    )

    cancel = subparsers.add_parser(
        "cancel",
        description="cancel a job",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    info = subparsers.add_parser(
        "info",
        description="get information for a job",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    logs = subparsers.add_parser(
        "logs",
        description="get log output for a job",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    logs.add_argument(
        "--stream",
        help="stream logs as they are available (does not block).",
        default=False,
        action="store_true",
    )

    subparsers.add_parser(
        "list-nodes",
        description="list node that the Flux RESTful API knows about",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers.add_parser(
        "list-jobs",
        description="list jobs that the Flux RESTful API knows about",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers.add_parser(
        "stop-service",
        description="Kill your Flux RESTFul API server (cannot be undone)",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    for command in cancel, info, logs:
        command.add_argument("jobid", help="The jobid to interact with.")

    return parser


def run_flux_restful_client():

    parser = get_parser()

    def help(return_code=0):
        """print help, including the software version and active client
        and exit with return code.
        """
        version = flux_restful_client.__version__

        print("\nFlux RESTFul Python Client v%s" % version)
        parser.print_help()
        sys.exit(return_code)

    # If the user didn't provide any arguments, show the full help
    if len(sys.argv) == 1:
        help()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, extra = parser.parse_known_args()

    if args.debug is True:
        os.environ["MESSAGELEVEL"] = "DEBUG"

    # Show the version and exit
    if args.command == "version" or args.version:
        print(flux_restful_client.__version__)
        sys.exit(0)

    setup_logger(
        quiet=args.quiet,
        debug=args.debug,
    )

    # retrieve subparser (with help) from parser
    helper = None
    subparsers_actions = [
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ]
    for subparsers_action in subparsers_actions:
        for choice, subparser in subparsers_action.choices.items():
            if choice == args.command:
                helper = subparser
                break

    if args.command == "info":
        from .info import main
    elif args.command == "cancel":
        from .cancel import main
    elif args.command == "config":
        from .config import main
    elif args.command == "logs":
        from .logs import main
    elif args.command == "stop-service":
        from .stop import stop_service as main
    elif args.command == "list-jobs":
        from .listing import list_jobs as main
    elif args.command == "list-nodes":
        from .listing import list_nodes as main
    elif args.command == "submit":
        from .submit import main
    elif args.command == "shell":
        from .shell import main

    # Pass on to the correct parser
    return_code = 0
    try:
        main(args=args, parser=parser, extra=extra, subparser=helper)
        sys.exit(return_code)
    except UnboundLocalError:
        return_code = 1

    help(return_code)


if __name__ == "__main__":
    run_flux_restful_client()
