-- Migration: add `email` column to `tutors` and backfill values
-- Usage (Supabase SQL editor): paste the contents and run.
-- Usage (psql):
--   PGPASSWORD=<pass> psql -h <host> -p <port> -U <user> -d <db> -f add_tutor_email_column_and_backfill.sql
-- The script is idempotent: it uses IF NOT EXISTS and skips already-filled rows.

BEGIN;

-- 1) Add column if missing
ALTER TABLE IF EXISTS public.tutors
  ADD COLUMN IF NOT EXISTS email text;

-- 2) Backfill from auth.users using linked user_id (most reliable)
UPDATE public.tutors t
SET email = u.email
FROM auth.users u
WHERE t.user_id IS NOT NULL
  AND u.id = t.user_id
  AND (t.email IS NULL OR t.email = '');

-- 3) Backfill from any bookings rows that may have captured a tutor email
-- (adjust column name if your bookings table stores tutor email under a different column)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='bookings' AND column_name='tutor_email') THEN
    UPDATE public.tutors t
    SET email = b.tutor_email
    FROM public.bookings b
    WHERE b.tutor_id IS NOT NULL
      AND b.tutor_id = t.id
      AND b.tutor_email IS NOT NULL
      AND (t.email IS NULL OR t.email = '');
  END IF;
END$$;

-- 4) Optional: create an index on email for faster lookups (no-op if exists)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname='public' AND tablename='tutors' AND indexname='tutors_email_idx') THEN
    CREATE INDEX tutors_email_idx ON public.tutors ((lower(email)));
  END IF;
END$$;

COMMIT;

-- Backfill verification notes:
-- After running, verify with:
--   SELECT id, user_id, email FROM public.tutors WHERE email IS NULL LIMIT 50;
