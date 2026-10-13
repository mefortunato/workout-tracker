#!/usr/bin/env bash
# Runs backend and frontend development servers in parallel

trap 'kill 0' EXIT

echo "Starting FastAPI backend on port 8000..."
cd "$(dirname "$0")/../backend"
uv run uvicorn app.main:app --reload --port 8000 &

echo "Starting Vite SvelteKit frontend on port 5173..."
cd "$(dirname "$0")/../frontend"
npm run dev &

wait
