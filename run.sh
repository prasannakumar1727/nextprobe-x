#!/usr/bin/env bash
# One-command launch: builds frontend if needed, serves API + UI on http://127.0.0.1:8000
set -e; cd "$(dirname "$0")"
[ -d frontend/node_modules ] || (cd frontend && npm install)
[ -d frontend/dist ] || (cd frontend && npm run build)
cd backend && exec python3 -m uvicorn nextprobe.api:app --host 127.0.0.1 --port 8000
