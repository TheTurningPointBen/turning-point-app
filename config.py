import os
from dotenv import load_dotenv

load_dotenv()

# Expose Supabase credentials for simple imports
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
