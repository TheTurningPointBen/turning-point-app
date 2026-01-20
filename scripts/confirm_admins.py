#!/usr/bin/env python3
"""Confirm existing Supabase users (and optionally set password) using service role key.

Usage:
  # confirm users by email
  python3 scripts/confirm_admins.py --email tanya@theturningpoint.co.za --email admin@theturningpoint.co.za

  # confirm and set password for a user
  python3 scripts/confirm_admins.py --email tanya@theturningpoint.co.za --password NewPass123!

This script requires `SUPABASE_URL` and `SUPABASE_KEY` (service role key) available
in the environment or in the repository `.env` file. The script will refuse to run
if the key looks like a publishable key (doesn't start with "service_role_").
"""
import os
import argparse
import sys
from pathlib import Path
import httpx
from dotenv import load_dotenv


def load_env():
    repo_root = Path(__file__).resolve().parents[1]
    dotenv_path = repo_root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=str(dotenv_path))


def get_config():
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    return SUPABASE_URL, SUPABASE_KEY


def ensure_service_key(key: str):
    if not key:
        return False, "SUPABASE_KEY not set"
    if not key.startswith("service_role_"):
        return False, "SUPABASE_KEY does not appear to be a service role key"
    return True, None


def find_user_by_email(base_url: str, headers: dict, email: str):
    url = f"{base_url}/auth/v1/admin/users?email={email}"
    r = httpx.get(url, headers=headers, timeout=30.0)
    r.raise_for_status()
    data = r.json()
    # API returns a list; if empty, return None
    if isinstance(data, list) and data:
        return data[0]
    return None


def confirm_user(base_url: str, headers: dict, user_id: str, password: str | None = None):
    url = f"{base_url}/auth/v1/admin/users/{user_id}"
    payload = {"email_confirm": True}
    if password:
        payload["password"] = password
    r = httpx.patch(url, headers=headers, json=payload, timeout=30.0)
    r.raise_for_status()
    return r.json()


def main():
    load_env()
    supabase_url, supabase_key = get_config()
    parser = argparse.ArgumentParser(description="Confirm Supabase users using service role key")
    parser.add_argument("--email", action="append", required=True, help="Email address to confirm (can repeat)")
    parser.add_argument("--password", help="Optional: set a new password for the user(s)")
    args = parser.parse_args()

    ok, msg = ensure_service_key(supabase_key)
    if not ok:
        print(f"Refusing to run: {msg}")
        print("Set SUPABASE_KEY to your service role key in .env or environment and try again.")
        sys.exit(2)

    if not supabase_url:
        print("SUPABASE_URL not set in environment or .env")
        sys.exit(2)

    headers = {
        "Authorization": f"Bearer {supabase_key}",
        "apikey": supabase_key,
        "Content-Type": "application/json",
    }

    for email in args.email:
        try:
            print(f"Looking up user: {email}")
            user = find_user_by_email(supabase_url, headers, email)
            if not user:
                print(f"User not found: {email}")
                continue
            user_id = user.get("id")
            print(f"Found user id: {user_id} — confirming")
            res = confirm_user(supabase_url, headers, user_id, password=args.password)
            print(f"Confirmed {email}: {res}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error for {email}: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"Error confirming {email}: {e}")


if __name__ == "__main__":
    main()
