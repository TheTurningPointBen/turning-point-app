from utils.session import get_supabase

EMAIL = 'ben@theturningpoin.co.za'
PASSWORD = 'Heronbridge@1'

try:
    supabase = get_supabase()
    try:
        res = supabase.auth.sign_in_with_password({
            'email': EMAIL,
            'password': PASSWORD
        })
        print('SIGN IN RESULT:')
        print(res)
    except Exception as e:
        print('SIGN IN EXCEPTION:')
        import traceback
        traceback.print_exc()
except Exception as e:
    print('FAILED TO CREATE SUPABASE CLIENT:')
    import traceback
    traceback.print_exc()
