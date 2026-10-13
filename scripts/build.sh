#!/usr/bin/env bash
set -e

echo "=== Building SvelteKit Frontend to Static HTML ==="
cd "$(dirname "$0")/../frontend"
npm run build

echo "=== Running Backend Pytest Test Suite with uv ==="
cd ../backend
uv run pytest tests/

echo "=== Build & Verification Complete! ==="
