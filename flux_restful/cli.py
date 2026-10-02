"""
The flux-restful command.

    flux-restful serve      start the server (run it under `flux start`, or
                            with FLUX_URI pointing at an instance)
    flux-restful init       create the database tables and the superuser
    flux-restful add-user   add a user
    flux-restful list-users list users
"""

import argparse
import sys

from flux_restful.version import __version__


def serve(args) -> None:
    import uvicorn

    uvicorn.run(
        "flux_restful.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
    )


def get_parser():
    parser = argparse.ArgumentParser(
        prog="flux-restful",
        description="The Flux RESTful API server",
    )
    parser.add_argument(
        "--version", action="version", version=f"flux-restful {__version__}"
    )
    sub = parser.add_subparsers(dest="command", title="commands")

    run = sub.add_parser("serve", help="start the server (under flux start)")
    run.add_argument("--host", default="0.0.0.0", help="bind address (0.0.0.0)")
    run.add_argument("--port", type=int, default=5000, help="port (5000)")
    run.add_argument(
        "--workers",
        type=int,
        default=1,
        help="uvicorn workers (1); all share FLUX_TOKEN_SIGNING_KEY",
    )
    run.add_argument("--log-level", default="info", help="uvicorn log level (info)")

    sub.add_parser("init", help="create the database tables and the superuser")
    add = sub.add_parser("add-user", help="add a user to the database")
    add.add_argument("username")
    add.add_argument("password")
    add.add_argument(
        "--superuser", action="store_true", help="make the user a superuser"
    )
    sub.add_parser("list-users", help="list users in the database")
    return parser


def main(argv=None) -> None:
    parser = get_parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(args)
    elif args.command in ("init", "add-user", "list-users"):
        # Imported here: it connects to the database on import
        from flux_restful.db import init_db

        if args.command == "init":
            init_db.init_db()
        elif args.command == "add-user":
            init_db.add_user(args.username, args.password, superuser=args.superuser)
        else:
            init_db.list_users()
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
