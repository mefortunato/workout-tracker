#!/usr/bin/env bash
# ==============================================================
# PULSEFIT - GOOGLE CLOUD RUN DEPLOYMENT SCRIPT
# ==============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "======================================================"
echo "⚡ PulseFit - Deploying to Google Cloud Run"
echo "======================================================"

# 1. Check if gcloud CLI is installed
if ! command -v gcloud &> /dev/null; then
  echo "❌ Error: Google Cloud SDK (gcloud) is not installed."
  echo ""
  echo "To install gcloud CLI on Linux:"
  echo "  curl https://sdk.cloud.google.com | bash"
  echo "  exec -l \$SHELL"
  echo "  gcloud init"
  echo ""
  echo "Or see: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

# 2. Check GCP Project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
  echo "⚠️  No GCP project currently active."
  echo "Please select or set your project:"
  echo "  gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

echo "✓ Active GCP Project: ${PROJECT_ID}"

# 3. Read environment variables from .env if present
if [ -f .env ]; then
  echo "✓ Loading configuration from .env..."
  # Export non-comment lines
  set -a
  source <(grep -v '^#' .env | grep -v '^$')
  set +a
fi

# Ensure required variables exist
MONGODB_URI="${MONGODB_URI:-}"
DATABASE_NAME="${DATABASE_NAME:-workout_tracker}"
JWT_SECRET="${JWT_SECRET:-super-secret-workout-tracker-token-key-change-in-prod-2026}"
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-workout-tracker}"

if [ -z "$MONGODB_URI" ]; then
  echo "❌ Error: MONGODB_URI is not set in .env."
  echo "Please set your MongoDB Atlas connection string in .env before deploying."
  exit 1
fi

echo "✓ Target Region: ${REGION}"
echo "✓ Service Name:  ${SERVICE_NAME}"

# 4. Enable Google Cloud APIs
echo ""
echo "🚀 Step 1/3: Enabling required Google Cloud APIs (Cloud Run & Cloud Build)..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project "${PROJECT_ID}"

# 5. Build and deploy container directly using Google Cloud Build & Cloud Run
echo ""
echo "🚀 Step 2/3: Building and deploying container to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "MONGODB_URI=${MONGODB_URI},DATABASE_NAME=${DATABASE_NAME},JWT_SECRET=${JWT_SECRET},ALLOW_DEV_LOGIN=true,GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}" \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --project "${PROJECT_ID}"

# 6. Retrieve Service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)' --project "${PROJECT_ID}")

echo ""
echo "======================================================"
echo "🎉 DEPLOYMENT SUCCESSFUL!"
echo "======================================================"
echo "Public App URL: ${SERVICE_URL}"
echo ""
echo "🚀 Step 3/3: Final Production Settings"
echo "1. Set FRONTEND_URL environment variable:"
echo "   gcloud run services update ${SERVICE_NAME} --region ${REGION} --update-env-vars FRONTEND_URL=${SERVICE_URL}"
echo ""
echo "2. In Google Cloud Console (https://console.cloud.google.com/apis/credentials):"
echo "   Add to your OAuth 2.0 Web Client:"
echo "   - Authorized JavaScript Origin: ${SERVICE_URL}"
echo "   - Authorized Redirect URI:      ${SERVICE_URL}/api/auth/google/callback"
echo ""
echo "3. In MongoDB Atlas (https://cloud.mongodb.com/):"
echo "   Under 'Network Access' -> 'IP Access List', ensure '0.0.0.0/0' is whitelisted"
echo "   so Cloud Run instances can reach your database."
echo "======================================================"
