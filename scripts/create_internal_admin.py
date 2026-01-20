#!/usr/bin/env python3
"""Create an admin user via Supabase from the command line.

Usage:
  python3 scripts/create_internal_admin.py --email admin@example.com --password Secret123

This script loads the project's `utils.database.supabase` client (so ensure
`SUPABASE_URL` and `SUPABASE_KEY` are set in .env or the environment).

It will try to use the admin API (`supabase.auth.api.create_user`) when
available; otherwise it falls back to `sign_up`.
"""
import argparse
import importlib.util
from pathlib import Path
import sys


def load_supabase():
    # Load utils.database in a robust way (works when run from scripts/)
    repo_root = Path(__file__).resolve().parents[1]
    db_path = repo_root / "utils" / "database.py"
    if not db_path.exists():
        raise RuntimeError(f"Could not find utils.database at {db_path}")

    spec = importlib.util.spec_from_file_location("database", str(db_path))
    database = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database)
    return database.supabase


def main():
    parser = argparse.ArgumentParser(description="Create an internal admin user in Supabase")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--confirm", action="store_true", help="Attempt to mark email as confirmed (if supported)")
    args = parser.parse_args()

    try:
        supabase = load_supabase()
    except Exception as e:
        print(f"Failed to load Supabase client: {e}")
        sys.exit(2)

    email = args.email
    password = args.password

    print(f"Creating admin user: {email}")

    # Prefer admin create_user API if available (bypasses confirmation)
    try:
        api = getattr(supabase.auth, "api", None)
        if api and hasattr(api, "create_user"):
            payload = {"email": email, "password": password}
            if args.confirm:
                payload["email_confirm"] = True
            res = api.create_user(payload)
            print("create_user response:", res)
            user = getattr(res, "user", None)
        else:
            # Fallback: use sign_up
            res = supabase.auth.sign_up({"email": email, "password": password})
            print("sign_up response:", res)
            user = getattr(res, 'user', None)

        if user:
            uid = getattr(user, 'id', None)
            print(f"User created with id: {uid}")
            print("Note: this script does not modify application tables. If your app expects an admin record in a specific table, insert it manually or extend this script.")
            sys.exit(0)
        else:
            error = getattr(res, 'error', None)
            print("User creation did not return a user object.")
            if error:
                print("Error:", error)
            else:
                print("Response:", res)
            sys.exit(1)

    except Exception as e:
        print(f"Exception while creating user: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
