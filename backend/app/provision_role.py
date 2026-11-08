"""Safely provision a role for an existing TrustVault account.

This command deliberately does not import the FastAPI application or run its
startup schema handling. It only reads the existing database and, with
``--apply``, updates one user's role in a transaction.
"""

import argparse
import sys

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

ALLOWED_ROLES = {"user", "admin", "auditor"}


class ProvisioningError(Exception):
    """An expected, safely reportable provisioning failure."""


def provision_role(email, role, *, session_factory=None, apply=False, require_postgresql=False):
    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        raise ProvisioningError("an email address is required")
    if role not in ALLOWED_ROLES:
        raise ProvisioningError("role must be one of: user, admin, auditor")
    if session_factory is None:
        # Keep configuration/engine creation inside main's guarded operation;
        # malformed URLs or connection errors must never print credentials.
        from app.database import SessionLocal

        session_factory = SessionLocal
    from app.models import User

    with session_factory.begin() as db:
        dialect = db.get_bind().dialect.name
        if require_postgresql and dialect != "postgresql":
            raise ProvisioningError("the configured database is not PostgreSQL; no changes were made")

        target = db.scalar(
            select(User)
            .where(func.lower(User.email) == normalized_email)
            .with_for_update()
        )
        if target is None:
            raise ProvisioningError(f"no existing account found for {normalized_email}")

        current_role = target.role
        if current_role == "admin" and role != "admin":
            admin_ids = db.scalars(
                select(User.id).where(User.role == "admin").with_for_update()
            ).all()
            if len(admin_ids) <= 1:
                raise ProvisioningError("cannot remove the last administrator")

        if current_role != role and apply:
            # Assign only this column; password, document, permission and audit
            # data remain untouched.
            target.role = role
            db.flush()

    return {
        "email": normalized_email,
        "current_role": current_role,
        "requested_role": role,
        "changed": current_role != role and apply,
        "apply": apply,
        "database": dialect,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Provision the role of an existing TrustVault account. Defaults to a read-only dry run."
    )
    parser.add_argument("--email", required=True, help="email of the existing account")
    parser.add_argument("--role", required=True, choices=sorted(ALLOWED_ROLES))
    parser.add_argument("--apply", action="store_true", help="commit the role change")
    parser.add_argument(
        "--require-postgresql",
        action="store_true",
        help="refuse to run unless DATABASE_URL connects to PostgreSQL",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        result = provision_role(
            args.email,
            args.role,
            apply=args.apply,
            require_postgresql=args.require_postgresql,
        )
    except ProvisioningError as error:
        print(f"Provisioning refused: {error}", file=sys.stderr)
        return 2
    except SQLAlchemyError:
        # Driver exceptions may contain a database URL. Never print them.
        print("Provisioning failed: database operation failed; no changes were committed.", file=sys.stderr)
        return 1

    if result["current_role"] == result["requested_role"]:
        state = "No change; account already has the requested role"
    elif result["apply"]:
        state = f"Updated role {result['current_role']} -> {result['requested_role']}"
    else:
        state = f"Dry run; would update role {result['current_role']} -> {result['requested_role']}"
    print(f"{state} for {result['email']} (database: {result['database']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
