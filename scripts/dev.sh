#!/usr/bin/env bash
# ==============================================================
# PULSEFIT - LOCAL DEVELOPMENT ENVIRONMENT SCRIPT
# ==============================================================
# Runs local MongoDB container, FastAPI backend, and Vite frontend.
# Forces local MongoDB connection regardless of production MONGODB_URI in .env.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

# 1. Load variables from root .env if present
if [ -f "${ROOT_DIR}/.env" ]; then
  echo "✓ Loading configuration from .env..."
  set -a
  source <(grep -v '^#' "${ROOT_DIR}/.env" | grep -v '^$')
  set +a
fi

# 2. Local overrides for development
LOCAL_MONGO_PORT="${MONGO_PORT:-27018}"
export MONGODB_URI="mongodb://127.0.0.1:${LOCAL_MONGO_PORT}"
export DATABASE_NAME="${DATABASE_NAME:-workout_tracker}"
export FRONTEND_URL="http://localhost:5173"
export ALLOW_DEV_LOGIN="true"

# 3. Ensure local MongoDB Docker container is running
echo "📦 Ensuring local MongoDB container is running on port ${LOCAL_MONGO_PORT}..."
docker compose up -d mongodb

echo "⚡ Dev Database: ${MONGODB_URI} (${DATABASE_NAME})"

trap 'echo "Stopping dev servers..."; kill 0' EXIT INT TERM

# 4. Start FastAPI backend with hot reloading
echo "🚀 Starting FastAPI backend on http://127.0.0.1:8000..."
cd "${ROOT_DIR}/backend"
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &

# 5. Start Vite SvelteKit frontend
echo "✨ Starting Vite SvelteKit frontend on http://localhost:5173..."
cd "${ROOT_DIR}/frontend"
npm run dev &

wait
