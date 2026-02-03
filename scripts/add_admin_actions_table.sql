-- Migration: add admin_actions audit table

BEGIN;

CREATE TABLE IF NOT EXISTS public.admin_actions (
  id SERIAL PRIMARY KEY,
  admin_email TEXT,
  action TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

COMMIT;
