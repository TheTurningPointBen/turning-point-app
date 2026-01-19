-- Run in Supabase SQL editor (or psql) to add a JSONB `children` column to the `parents` table.
-- This allows storing multiple children per parent as an array of JSON objects.

ALTER TABLE parents
  ADD COLUMN IF NOT EXISTS children jsonb;

-- Optionally add a GIN index to speed searches within the JSONB column:
-- CREATE INDEX IF NOT EXISTS parents_children_idx ON parents USING gin (children jsonb_path_ops);

-- If you prefer to enforce a structure, you can add a CHECK using json_schema or constraints,
-- but for simplicity we store an array of objects like: [{"name":"Alice","grade":"4","school":"XYZ"}, ...]
