"""
Example admin actions script for manual testing.

Usage:
  # Dry run (default) - inserts a sample admin_actions row only if --apply
  python3 scripts/example_admin_actions.py --help

Environment:
  SUPABASE_URL and SUPABASE_SERVICE_ROLE must be set to run.

This script will:
- Connect to Supabase using the service role key via `get_supabase_service()`
- Optionally insert a sample `admin_actions` row (requires `--apply`)
- Fetch and print the most recent admin actions

WARNING: Destructive operations (deleting users or setting passwords) are disabled
unless you pass `--perform-destructive` and explicitly provide necessary IDs.
"""

import os
import json
import argparse
from datetime import datetime

from utils.session import get_supabase_service


def main():
    parser = argparse.ArgumentParser(description='Example admin actions script')
    parser.add_argument('--apply', action='store_true', help='Apply changes (insert sample audit row)')
    parser.add_argument('--limit', type=int, default=10, help='Number of recent actions to fetch')
    parser.add_argument('--perform-destructive', action='store_true', help='Allow destructive actions (disabled by default)')
    parser.add_argument('--delete-user-id', type=str, help='If --perform-destructive, delete this auth user id')
    parser.add_argument('--set-password-for', type=str, help='If --perform-destructive, set a temp password for this auth user id')
    args = parser.parse_args()

    url = os.getenv('SUPABASE_URL')
    svc_key = os.getenv('SUPABASE_SERVICE_ROLE')
    if not url or not svc_key:
        print('SUPABASE_URL and SUPABASE_SERVICE_ROLE must be set in the environment to run this script')
        return

    svc = get_supabase_service()

    if args.apply:
        print('Inserting sample admin_actions row...')
        payload = {
            'admin_email': os.getenv('ADMIN_EMAIL', os.getenv('SENDER_EMAIL', 'admin@example.com')),
            'action': 'example_insert',
            'target_type': 'script',
            'target_id': 'example-1',
            'details': {'note': f'Inserted at {datetime.utcnow().isoformat()}'}
        }
        try:
            ins = svc.table('admin_actions').insert(payload).execute()
            print('Insert result:', getattr(ins, 'data', None), getattr(ins, 'error', None))
        except Exception as e:
            print('Failed to insert admin_actions row:', e)

    print(f'Fetching last {args.limit} admin actions...')
    try:
        res = svc.table('admin_actions').select('*').order('created_at', desc=True).limit(args.limit).execute()
        rows = res.data or []
        for r in rows:
            print(json.dumps(r, default=str))
    except Exception as e:
        print('Failed to fetch admin actions:', e)

    # Optional destructive demo (must be explicitly enabled)
    if args.perform_destructive:
        if args.delete_user_id:
            print(f'Deleting auth user {args.delete_user_id} (destructive)')
            try:
                # Reuse the admin API via Supabase admin endpoint
                from utils.session import delete_auth_user
                r = delete_auth_user(args.delete_user_id)
                print('delete_auth_user result:', r)
            except Exception as e:
                print('Failed to delete auth user:', e)

        if args.set_password_for:
            print(f'Setting temporary password for {args.set_password_for} (destructive)')
            try:
                from utils.session import set_auth_user_password
                new_pw = 'TempPass1234'
                r = set_auth_user_password(args.set_password_for, new_pw)
                print('set_auth_user_password result:', r)
                print('Note: service set password but you must ensure user knows it via your normal email flow')
            except Exception as e:
                print('Failed to set password:', e)


if __name__ == '__main__':
    main()
