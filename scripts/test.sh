#!/usr/bin/env bash
# Runs every unit/integration suite. Add --e2e to also run the browser test (needs Playwright + Chromium).
set -e
cd "$(dirname "$0")/.."
echo "== backend (pytest) =="; (cd backend && python3 -m pytest -q)
echo "== frontend typecheck + vitest =="; (cd frontend && npx tsc --noEmit && npx vitest run)
if [ "$1" = "--e2e" ]; then echo "== e2e =="; (cd frontend && npm run build >/dev/null) && python3 scripts/e2e_screenshots.py; fi
