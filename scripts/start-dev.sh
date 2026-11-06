#!/usr/bin/env bash
# Backend on :8000, frontend dev server on :5173 (proxying /api to the backend)
cd "$(dirname "$0")/.."
(cd backend && python3 -m uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev)
