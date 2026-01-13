-- Run once in Supabase SQL editor
-- Adds boolean columns for Afrikaans and IsiZulu language capabilities
ALTER TABLE tutors
  ADD COLUMN IF NOT EXISTS speaks_afrikaans boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS speaks_isizulu boolean DEFAULT false;
