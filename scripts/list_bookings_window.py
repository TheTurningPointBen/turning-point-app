#!/usr/bin/env python3
"""List bookings from start of today through the next N hours (default 48)."""
from pathlib import Path
from datetime import datetime, timedelta
import json
import os
import importlib.util


def load_supabase():
    repo_root = Path(__file__).resolve().parents[1]
    db_path = repo_root / "utils" / "database.py"
    spec = importlib.util.spec_from_file_location("database", str(db_path))
    database = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(database)
    return database.supabase


def main():
    supabase = load_supabase()
    now = datetime.now()
    start_of_day = datetime(now.year, now.month, now.day)
    cutoff = now + timedelta(hours=48)

    start_date = start_of_day.date().isoformat()
    cutoff_date = cutoff.date().isoformat()

    print(f"Querying bookings with exam_date between {start_date} and {cutoff_date} (post-filtering to {start_of_day} -> {cutoff})")

    try:
        res = supabase.table("bookings").select("*").gte("exam_date", start_date).lte("exam_date", cutoff_date).execute()
    except Exception as e:
        print("Failed to query bookings:", e)
        return

    rows = res.data or []
    matches = []
    for b in rows:
        try:
            date_str = b.get('exam_date')
            time_str = b.get('start_time') or '00:00:00'
            dt = datetime.combine(datetime.fromisoformat(date_str), datetime.strptime(time_str, "%H:%M:%S").time())
        except Exception:
            continue
        if start_of_day <= dt <= cutoff:
            matches.append({
                'id': b.get('id'),
                'exam_date': date_str,
                'start_time': time_str,
                'child_name': b.get('child_name'),
                'subject': b.get('subject'),
                'status': b.get('status'),
                'tutor_id': b.get('tutor_id'),
            })

    print(json.dumps({'count': len(matches), 'window_start': start_of_day.isoformat(), 'window_end': cutoff.isoformat(), 'bookings': matches}, indent=2, default=str))


if __name__ == '__main__':
    main()
