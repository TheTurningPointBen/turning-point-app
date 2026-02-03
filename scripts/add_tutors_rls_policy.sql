/* Migration: enable Row Level Security and add policies for `tutors` */


-- Enable RLS on tutors
ALTER TABLE public.tutors ENABLE ROW LEVEL SECURITY;

-- Allow public SELECT only for approved tutors (useful for listing tutors to parents)
CREATE POLICY tutors_select_public_approved ON public.tutors
  FOR SELECT
  TO public
  USING (approved = true);

-- Allow authenticated users to SELECT their own tutor row
CREATE POLICY tutors_select_owner ON public.tutors
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Allow authenticated users to INSERT only when their auth.uid() matches new.user_id
CREATE POLICY tutors_insert_owner ON public.tutors
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = new.user_id);

-- Allow authenticated users to UPDATE only their own row
CREATE POLICY tutors_update_owner ON public.tutors
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = new.user_id);

COMMIT;
