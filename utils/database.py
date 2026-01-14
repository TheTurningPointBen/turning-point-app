import os
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions
from dotenv import load_dotenv
from pathlib import Path
import httpx
from typing import Any

# Load .env from repository root (robust when Streamlit changes CWD)
repo_root = Path(__file__).resolve().parents[1]
dotenv_path = repo_root / ".env"
load_dotenv(dotenv_path=str(dotenv_path))

# Read credentials from environment (or .env)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class _MissingSupabase:
    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(
            f"Supabase client not configured: SUPABASE_URL and SUPABASE_KEY must be set in the environment or .env (looked in {dotenv_path})"
        )


if not SUPABASE_URL or not SUPABASE_KEY:
    # Avoid raising at import time; provide a clear runtime error when used.
    supabase = _MissingSupabase()
else:
    # Create HTTP client with longer timeout
    http_client = httpx.Client(timeout=30.0)

    # Supply a SyncClientOptions instance so the client uses our httpx client
    options = SyncClientOptions(httpx_client=http_client)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)
