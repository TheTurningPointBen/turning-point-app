-- Run this once in the Supabase SQL editor to add cancellation columns
alter table bookings
add column cancelled boolean default false,
add column cancelled_at timestamp;

-- Optionally you can also add a status value 'Cancelled' but the boolean and timestamp are sufficient
