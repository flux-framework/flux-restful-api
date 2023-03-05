import argparse
import logging
import os
import sys

# Ensure we have root on Pythonpath

here = os.path.dirname(__file__)
root = os.path.dirname(os.path.dirname(here))
print(root)

if root not in sys.path:
    sys.path.insert(0, root)

import app.schemas as schemas  # noqa
from app.db.session import SessionLocal  # noqa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flux-restful")

import app.crud.user as crud_user  # noqa
from app.core.config import settings  # noqa

# make sure all SQL Alchemy models are imported (app.db.base) before initializing DB
# otherwise, SQL Alchemy might fail to initialize relationships properly
# for more details: https://github.com/tiangolo/full-stack-fastapi-postgresql/issues/28


def init_db() -> None:
    """
    Create the Flux Restful Superuser (and testing account)

    These can eventually be linked to server accounts that are
    associated with user ids. That doesn't seem necessary yet given
    the primarily single / few user use cases.
    """
    if not settings.flux_user or not settings.flux_token:
        sys.exit("Please export FLUX_USER and FLUX_TOKEN to create the superuser.")
    logger.info("Creating initial data")
    add_user(settings.flux_user, settings.flux_token, superuser=True)
    logger.info("Initial data created")


def list_users():
    """
    List users in the database.
    """
    db = SessionLocal()
    for user in crud_user.get_multi(db):
        logger.info(user)


def add_user(username, password, superuser=False, is_active=True) -> None:
    """
    One off function to add a user to the database
    """
    username = username.strip()
    password = password.strip()
    db = SessionLocal()

    user = crud_user.get_by_username(db, user_name=username)
    if not user:
        user_in = schemas.UserCreate(
            user_name=username,
            password=password,
            is_superuser=superuser,
            is_active=is_active,
        )
        user = crud_user.create(db, obj_in=user_in)  # noqa: F841
        logger.info(f"User {username} has been created.")


def main() -> None:
    parser = get_parser()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, _ = parser.parse_known_args()
    if args.command == "init":
        init_db()
    elif args.command == "list-users":
        list_users()
    elif args.command == "add-user":
        add_user(args.username, args.password)
    else:
        sys.exit(f"{args.command} is not recognized.")


def get_parser():
    parser = argparse.ArgumentParser(
        description="Flux Restful Database",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        help="actions",
        title="actions",
        description="actions",
        dest="command",
    )

    # Submit a job (all extra is the command)
    add_user = subparsers.add_parser(
        "add-user",
        description="add a new user and password to the database",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_user.add_argument("username", help="username")
    add_user.add_argument("password", help="password")

    # Local shell with client loaded
    subparsers.add_parser(
        "init",
        description="initialize the database",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    return parser


if __name__ == "__main__":
    main()
