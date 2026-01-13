import importlib.util
from pathlib import Path

db_path = Path(__file__).parents[1] / "utils" / "database.py"
spec = importlib.util.spec_from_file_location("database", str(db_path))
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)

supabase = database.supabase

email = "test_parent@example.com"
password = "TestPass123!"

print('Creating test account:', email)
try:
    res = supabase.auth.sign_up({"email": email, "password": password})
    print('signup_raw:', res)
    user = getattr(res, 'user', None)
    print('signup_user:', user)
except Exception as e:
    print('signup_exception:', repr(e))

try:
    res2 = supabase.auth.sign_in_with_password({"email": email, "password": password})
    print('signin_raw:', res2)
    user2 = getattr(res2, 'user', None)
    print('signin_user:', user2)
except Exception as e:
    print('signin_exception:', repr(e))
