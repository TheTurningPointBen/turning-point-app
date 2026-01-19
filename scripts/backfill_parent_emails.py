"""Backfill parent emails from bookings into parents table.

This script updates existing parents rows where the `email` is missing
but the related booking contains a `parent_email` or `email` field.

Run locally with:
    python3 scripts/backfill_parent_emails.py

It will not create new parent records or modify booking.parent_id values.
"""

from utils.database import supabase

if __name__ == '__main__':
    print("Fetching bookings...")
    try:
        b_res = supabase.table('bookings').select('id,parent_id,parent_email,email').execute()
    except Exception as e:
        print(f"Failed to query bookings: {e}")
        raise

    rows = getattr(b_res, 'data', None) or []
    updated = 0
    skipped_no_parent = 0
    skipped_no_email = 0

    for b in rows:
        bid = b.get('id')
        pid = b.get('parent_id')
        booking_email = (b.get('parent_email') or b.get('email') or None)
        if not pid:
            skipped_no_parent += 1
            continue
        if not booking_email:
            skipped_no_email += 1
            continue

        try:
            p_res = supabase.table('parents').select('id,email').eq('id', pid).execute()
            pdata = getattr(p_res, 'data', None) or []
            if not pdata:
                print(f"Booking {bid}: parent_id={pid} missing in parents table; skipping.")
                continue
            existing = pdata[0]
            if existing.get('email'):
                # already populated
                continue
            upd = supabase.table('parents').update({'email': booking_email}).eq('id', pid).execute()
            if getattr(upd, 'error', None) is None:
                print(f"Updated parent id={pid} with email={booking_email}")
                updated += 1
            else:
                print(f"Failed update for parent id={pid}: {getattr(upd, 'error', None)}")
        except Exception as e:
            print(f"Error processing booking {bid}: {e}")

    print("---")
    print(f"Rows scanned: {len(rows)}")
    print(f"Parents updated: {updated}")
    print(f"Skipped (no parent_id): {skipped_no_parent}")
    print(f"Skipped (no booking email): {skipped_no_email}")
    print("Done.")
