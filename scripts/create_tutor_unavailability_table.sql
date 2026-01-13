-- Run once in Supabase SQL editor to create a table for tutor unavailability
create table if not exists tutor_unavailability (
  id uuid DEFAULT gen_random_uuid() primary key,
  tutor_id uuid not null references tutors(id) on delete cascade,
  start_date date not null,
  end_date date not null,
  start_time time, -- optional: if provided, unavailability applies between start_time and end_time each day in the range
  end_time time,
  reason text,
  created_at timestamp with time zone default now()
);

-- Add an index for fast lookup by tutor and date
create index if not exists idx_tutor_unavail_tutor_date on tutor_unavailability (tutor_id, start_date, end_date);
