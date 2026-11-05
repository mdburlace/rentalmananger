"""Reset a user's password from the command line (for when you're locked out).

Run inside the container:

    docker exec -it rentalmanager python -m app.reset_password            # list accounts
    docker exec -it rentalmanager python -m app.reset_password you@example.com

You'll be asked for the new password twice (it isn't echoed or saved in shell history).
The account is also re-enabled if it had been deactivated.
"""
from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from .db import SessionLocal
from .models import User
from .security import hash_password

MIN_LENGTH = 8


def list_users(db) -> None:
    users = db.scalars(select(User).order_by(User.email)).all()
    if not users:
        print("No accounts exist yet - open the app in a browser to run first-time setup.")
        return
    print("Accounts:")
    for u in users:
        status = "" if u.is_active else "  (deactivated)"
        print(f"  {u.email:<40} {u.role}{status}")


def prompt_password() -> str:
    while True:
        pw = getpass.getpass("New password: ")
        if len(pw) < MIN_LENGTH:
            print(f"Password must be at least {MIN_LENGTH} characters.")
            continue
        if getpass.getpass("Confirm new password: ") != pw:
            print("Passwords didn't match, try again.")
            continue
        return pw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.reset_password",
                                     description="Reset a Rental Manager user's password.")
    parser.add_argument("email", nargs="?", help="login email of the account (omit to list accounts)")
    parser.add_argument("--password", help="new password (skips the prompt; avoid - it ends up in shell history)")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        if not args.email:
            list_users(db)
            return 0

        email = args.email.strip().lower()
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            print(f"No account found for '{email}'.")
            list_users(db)
            return 1

        if args.password is not None:
            if len(args.password) < MIN_LENGTH:
                print(f"Password must be at least {MIN_LENGTH} characters.")
                return 1
            new_pw = args.password
        else:
            new_pw = prompt_password()

        user.password_hash = hash_password(new_pw)
        reactivated = not user.is_active
        user.is_active = True
        db.commit()

    print(f"Password reset for {email}." + (" Account re-enabled." if reactivated else ""))
    print("You can now log in with the new password.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
