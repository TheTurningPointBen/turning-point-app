# The Turning Point — Streamlit App

This repository contains the Streamlit app used by The Turning Point.

## Quick environment
- Python 3.10+ recommended
- Install dependencies:

```powershell
pip install -r requirements.txt
```

## Run locally
```powershell
# from repo root
python -m streamlit run turning_point_app/streamlit_app.py
```

## Git -> Deploy (Streamlit Cloud)
1. Commit & push your code to GitHub:
```powershell
git add .
git commit -m "Initial deployment"
git branch -M main
# if no remote set (replace URL):
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```
2. On Streamlit Cloud (https://share.streamlit.io):
- Sign in with GitHub
- New app → select your repo
- Branch: `main`
- Main file path: `turning_point_app/streamlit_app.py`
- Click Deploy

## Database / Migrations
- A SQL migration to add tutor language columns is at `scripts/add_tutor_language_columns.sql` (run once in Supabase SQL editor or via psql / supabase CLI).

## Environment variables
Create a `.env` in the project root or set environment variables in your deployment platform for:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` (if using SMTP email)

## Password reset URL (Supabase integration)
This app includes a dedicated password reset page at `/password_reset` which handles Supabase recovery links of the form:

	?type=recovery&access_token=<token>

To enable in-app password resets, set the Supabase Auth "Site URL" / "Redirect URL" to your app's base URL plus `/password_reset`. Example:

	https://your-app.example.com/password_reset

Then, configure SMTP in the Supabase Dashboard (Authentication → Settings → SMTP) so Supabase can send recovery emails. Use an application-specific SMTP password (e.g. Gmail App Password) and test with the "Send test email" control.

After updating, try the "Forgot password" flow in the app — recovery links will open the `password_reset` page and allow users to set a new password.

## Notes
- The app entry is `turning_point_app/streamlit_app.py` (Streamlit Cloud expects a main file path).
- Language fields for tutors exist in the DB migration script but language UI is disabled in the app; you can enable later if needed.

If you want, I can add a short LICENSE or CONTRIBUTING file next.
