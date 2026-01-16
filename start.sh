#!/usr/bin/env bash
set -euo pipefail

echo "--- start.sh diagnostics ---"
echo "PWD: $(pwd)"
echo "Listing repo root:"
ls -la
echo "--- Python & Streamlit versions ---"
python3 --version || true
streamlit --version || true
echo "--- Filtered env ---"
env | grep -E 'PORT|RAILWAY|DATABASE_URL|SUPABASE|GIT' || true
echo "--- Starting Streamlit ---"

exec streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port ${PORT:-8501} --server.headless true --server.enableCORS false --server.enableXsrfProtection false
