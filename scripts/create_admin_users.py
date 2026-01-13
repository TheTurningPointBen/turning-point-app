import importlib.util
from pathlib import Path

# load utils.database
db_path = Path(__file__).parents[1] / "utils" / "database.py"
spec = importlib.util.spec_from_file_location("database", str(db_path))
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)

supabase = database.supabase

admins = [
    ("ben@theturningpoint.co.za", "Heronbridge@1"),
    ("admin@theturningpoint.co.za", "Turn1ngp01nt"),
]

for email, password in admins:
    print(f"Creating admin: {email}")
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        print('signup_raw:', res)
        user = getattr(res, 'user', None)
        error = getattr(res, 'error', None)
        if user:
            print(f"Signup succeeded for {email}. User id: {getattr(user,'id', None)}")
        elif error:
            print(f"Signup error for {email}: {error}")
        else:
            print(f"Signup response for {email}: {res}")

        # try sign in to verify (may require email confirmation)
        try:
            signin = supabase.auth.sign_in_with_password({"email": email, "password": password})
            print('signin_raw:', signin)
            suser = getattr(signin, 'user', None)
            serror = getattr(signin, 'error', None)
            if suser:
                print(f"Signin succeeded for {email}.")
            elif serror:
                print(f"Signin error for {email}: {serror}")
            else:
                print(f"Signin response for {email}: {signin}")
        except Exception as e:
            print(f"Signin attempt exception for {email}: {e}")

    except Exception as e:
        print(f"Exception creating {email}: {e}")

print('Done')
