"""
Database setup: create the tables and manage users.

Used by the `flux-restful` command (init, add-user, list-users) and runnable
directly with `python3 -m flux_restful.db.init_db`.
"""

import argparse
import logging
import sys

import flux_restful.crud.user as crud_user
import flux_restful.schemas as schemas
from flux_restful.core.config import settings

# Import all models so SQLAlchemy knows every table before create_all
from flux_restful.db.base import Base
from flux_restful.db.session import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flux-restful")


def create_tables() -> None:
    """
    Create any missing tables (a no-op for existing ones).
    """
    Base.metadata.create_all(bind=engine)


def init_db() -> None:
    """
    Create the tables and the superuser from FLUX_USER / FLUX_TOKEN.
    """
    if not settings.flux_user or not settings.flux_token:
        sys.exit("Please export FLUX_USER and FLUX_TOKEN to create the superuser.")
    create_tables()
    logger.info("Creating initial data")
    add_user(settings.flux_user, settings.flux_token, superuser=True)
    logger.info("Initial data created")


def list_users():
    """
    List users in the database.
    """
    create_tables()
    db = SessionLocal()
    users = crud_user.get_multi(db)
    for user in users:
        flags = []
        if user.is_superuser:
            flags.append("superuser")
        if not user.is_active:
            flags.append("inactive")
        logger.info("%s %s", user.user_name, " ".join(flags))
    return users


def add_user(username, password, superuser=False, is_active=True) -> None:
    """
    Add a user to the database (no-op if the username exists).
    """
    username = username.strip()
    password = password.strip()
    create_tables()
    db = SessionLocal()

    user = crud_user.get_by_username(db, user_name=username)
    if user:
        logger.info(f"User {username} already exists.")
        return
    user_in = schemas.UserCreate(
        user_name=username,
        password=password,
        is_superuser=superuser,
        is_active=is_active,
    )
    try:
        crud_user.create(db, obj_in=user_in)
    except ValueError as e:
        # e.g., a password longer than bcrypt's 72 byte limit
        sys.exit(f"Cannot create user {username}: {e}")
    logger.info(f"User {username} has been created.")


def main(argv=None) -> None:
    parser = get_parser()

    # If an error occurs while parsing the arguments, the interpreter will exit with value 2
    args, _ = parser.parse_known_args(argv)
    if args.command == "init":
        init_db()
    elif args.command == "list-users":
        list_users()
    elif args.command == "add-user":
        add_user(args.username, args.password, superuser=args.superuser)
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
    subparsers.add_parser(
        "list-users",
        description="list existing users",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_user = subparsers.add_parser(
        "add-user",
        description="add a new user and password to the database",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_user.add_argument("username", help="username")
    add_user.add_argument("password", help="password")
    add_user.add_argument(
        "--superuser", action="store_true", help="make the user a superuser"
    )
    subparsers.add_parser(
        "init",
        description="create the tables and the FLUX_USER superuser",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    return parser


if __name__ == "__main__":
    main()
