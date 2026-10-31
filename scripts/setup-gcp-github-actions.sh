#!/usr/bin/env bash
# ==============================================================
# PULSEFIT - ONE-TIME GCP SETUP FOR GITHUB ACTIONS DEPLOYS
# ==============================================================
# Prepares a GCP project for .github/workflows/deploy-cloud-run.yml:
#   1. Enables the required APIs
#   2. Creates the Artifact Registry Docker repository
#   3. Stores MONGODB_URI, JWT_SECRET, GOOGLE_CLIENT_SECRET in Secret Manager
#   4. Creates a deployer service account with the roles the workflow needs
#   5. Creates a Workload Identity Federation pool + provider restricted to
#      this GitHub repository (keyless auth, no JSON keys)
#   6. Prints the `gh` commands to configure GitHub secrets & variables
#
# Safe to re-run: existing resources are reused, and secrets only get a new
# version when the value changed.
#
# Usage:
#   ./scripts/setup-gcp-github-actions.sh [-y]
#
# Values are read from the environment or the root .env file:
#   MONGODB_URI, JWT_SECRET, GOOGLE_CLIENT_SECRET, GOOGLE_CLIENT_ID,
#   DATABASE_NAME, CUSTOM_DOMAIN, FRONTEND_URL, ALLOW_DEV_LOGIN
# Optional overrides:
#   PROJECT_ID, REGION (us-central1), SERVICE_NAME (workout-tracker),
#   AR_REPO (cloud-run-source-deploy), GITHUB_REPO (owner/repo),
#   DEPLOYER_SA_NAME (github-deployer), WIF_POOL (github),
#   WIF_PROVIDER (github-oidc)
# ==============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${ROOT_DIR}"

ASSUME_YES=false
for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=true ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 1 ;;
  esac
done

step() { echo ""; echo "🚀 $*"; }
ok()   { echo "   ✓ $*"; }
info() { echo "   ℹ️  $*"; }
die()  { echo "❌ Error: $*" >&2; exit 1; }

echo "======================================================"
echo "⚡ PulseFit - GCP setup for GitHub Actions deploys"
echo "======================================================"

command -v gcloud >/dev/null 2>&1 || die "gcloud CLI is not installed (https://cloud.google.com/sdk/docs/install)."

# --------------------------------------------------------------
# Configuration
# --------------------------------------------------------------
# Remember explicit caller overrides so .env does not clobber them
# (plain variables rather than an associative array, for macOS bash 3.2).
OVERRIDABLE="PROJECT_ID REGION SERVICE_NAME AR_REPO GITHUB_REPO MONGODB_URI JWT_SECRET
  GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET DATABASE_NAME CUSTOM_DOMAIN FRONTEND_URL ALLOW_DEV_LOGIN"
for v in $OVERRIDABLE; do
  if [ -n "${!v:-}" ]; then printf -v "CALLER_$v" '%s' "${!v}"; fi
done

if [ -f .env ]; then
  echo "✓ Loading configuration from .env"
  set -a
  # shellcheck disable=SC1090
  source <(grep -v '^[[:space:]]*#' .env | grep -v '^[[:space:]]*$')
  set +a
fi
for v in $OVERRIDABLE; do
  c="CALLER_$v"
  if [ -n "${!c:-}" ]; then printf -v "$v" '%s' "${!c}"; fi
done

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
[ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" != "(unset)" ] \
  || die "No GCP project. Run 'gcloud config set project YOUR_PROJECT_ID' or set PROJECT_ID."

REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-workout-tracker}"
AR_REPO="${AR_REPO:-cloud-run-source-deploy}"
DEPLOYER_SA_NAME="${DEPLOYER_SA_NAME:-github-deployer}"
WIF_POOL="${WIF_POOL:-github}"
WIF_PROVIDER="${WIF_PROVIDER:-github-oidc}"
DATABASE_NAME="${DATABASE_NAME:-workout_tracker}"
ALLOW_DEV_LOGIN="${ALLOW_DEV_LOGIN:-false}"
MONGODB_URI="${MONGODB_URI:-}"
JWT_SECRET="${JWT_SECRET:-}"
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
CUSTOM_DOMAIN="${CUSTOM_DOMAIN:-}"
FRONTEND_URL="${FRONTEND_URL:-}"

# Derive owner/repo from the git remote unless given explicitly.
if [ -z "${GITHUB_REPO:-}" ]; then
  REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
  GITHUB_REPO="$(echo "$REMOTE_URL" | sed -E 's#\.git$##; s#^.*[:/]([^/]+/[^/]+)$#\1#')"
fi
[[ "$GITHUB_REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] \
  || die "Could not determine the GitHub repository. Set GITHUB_REPO=owner/repo."

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')" \
  || die "Cannot read project ${PROJECT_ID}. Check 'gcloud auth login' and your permissions."
DEPLOYER_SA="${DEPLOYER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
# Cloud Run revisions run as the Compute Engine default SA (the workflow does not override it).
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
WIF_PROVIDER_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER}"

# The app refuses to start in production with a weak JWT secret.
GENERATED_JWT=false
case "$JWT_SECRET" in
  super-secret-workout-tracker-token-key-*|changeme|secret)
    die "JWT_SECRET uses a publicly known default. Replace it in .env." ;;
esac
if [ -z "$JWT_SECRET" ]; then
  JWT_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))' 2>/dev/null \
    || openssl rand -base64 48 | tr -d '\n=+/')"
  GENERATED_JWT=true
elif [ "${#JWT_SECRET}" -lt 32 ]; then
  die "JWT_SECRET must be at least 32 characters."
fi

# The app enables Google Sign-In whenever the secret is non-empty, so no placeholders.
[ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ] \
  || die "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set (OAuth 2.0 Web client from https://console.cloud.google.com/apis/credentials)."

[ -n "$MONGODB_URI" ] || die "MONGODB_URI is not set (add your MongoDB Atlas connection string to .env)."
case "$MONGODB_URI" in
  *localhost*|*127.0.0.1*|mongodb://mongodb:*)
    die "MONGODB_URI points at a local database (${MONGODB_URI%%@*}...). Use your MongoDB Atlas URI." ;;
esac

echo ""
echo "Project:          ${PROJECT_ID} (#${PROJECT_NUMBER})"
echo "Region:           ${REGION}"
echo "Service:          ${SERVICE_NAME}"
echo "Artifact repo:    ${AR_REPO}"
echo "GitHub repo:      ${GITHUB_REPO}"
echo "Deployer SA:      ${DEPLOYER_SA}"
echo "Runtime SA:       ${RUNTIME_SA}"
echo "WIF provider:     ${WIF_PROVIDER_RESOURCE}"
if $GENERATED_JWT; then echo "⚠️  JWT_SECRET was not set; a new random one will be generated and stored."; fi

if ! $ASSUME_YES; then
  echo ""
  read -r -p "Proceed with these settings? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
fi

# --------------------------------------------------------------
# 1. APIs
# --------------------------------------------------------------
step "1/6 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project "$PROJECT_ID"
ok "APIs enabled"

if ! gcloud iam service-accounts describe "$RUNTIME_SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  info "Compute Engine default SA not found; enabling compute.googleapis.com to create it..."
  gcloud services enable compute.googleapis.com --project "$PROJECT_ID"
  for _ in 1 2 3 4 5 6; do
    gcloud iam service-accounts describe "$RUNTIME_SA" --project "$PROJECT_ID" >/dev/null 2>&1 && break
    sleep 10
  done
  gcloud iam service-accounts describe "$RUNTIME_SA" --project "$PROJECT_ID" >/dev/null 2>&1 \
    || die "Runtime service account ${RUNTIME_SA} does not exist."
fi
ok "Runtime SA ${RUNTIME_SA} exists"

# --------------------------------------------------------------
# 2. Artifact Registry
# --------------------------------------------------------------
step "2/6 Artifact Registry repository..."
if gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  ok "Repository ${AR_REPO} already exists"
else
  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker --location "$REGION" --project "$PROJECT_ID" \
    --description="Cloud Run images for ${SERVICE_NAME}"
  ok "Created repository ${AR_REPO}"
fi

# --------------------------------------------------------------
# 3. Secret Manager
# --------------------------------------------------------------
step "3/6 Secret Manager secrets..."
upsert_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" --project "$PROJECT_ID" >/dev/null 2>&1; then
    local current
    current="$(gcloud secrets versions access latest --secret "$name" --project "$PROJECT_ID" 2>/dev/null || true)"
    if [ "$current" == "$value" ]; then
      ok "${name}: unchanged"
      return
    fi
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- --project "$PROJECT_ID" >/dev/null
    ok "${name}: added new version"
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- \
      --replication-policy=automatic --project "$PROJECT_ID" >/dev/null
    ok "${name}: created"
  fi
  gcloud secrets add-iam-policy-binding "$name" --project "$PROJECT_ID" \
    --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor \
    --condition=None >/dev/null
}
upsert_secret MONGODB_URI "$MONGODB_URI"
upsert_secret JWT_SECRET "$JWT_SECRET"
upsert_secret GOOGLE_CLIENT_SECRET "$GOOGLE_CLIENT_SECRET"
ok "Runtime SA can read the secrets"

# --------------------------------------------------------------
# 4. Deployer service account
# --------------------------------------------------------------
step "4/6 Deployer service account..."
if gcloud iam service-accounts describe "$DEPLOYER_SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  ok "${DEPLOYER_SA} already exists"
else
  gcloud iam service-accounts create "$DEPLOYER_SA_NAME" --project "$PROJECT_ID" \
    --display-name="GitHub Actions deployer (${GITHUB_REPO})"
  ok "Created ${DEPLOYER_SA}"
  sleep 5 # IAM propagation
fi

# run.admin: deploy + set public invoker. artifactregistry.repoAdmin (on the repo):
# push images and manage cleanup policies. storage.admin: the cleanup script sets
# lifecycle rules on the run-sources bucket.
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role=roles/run.admin --condition=None >/dev/null
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role=roles/storage.admin --condition=None >/dev/null
gcloud artifacts repositories add-iam-policy-binding "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role=roles/artifactregistry.repoAdmin >/dev/null
# Allow the deployer to deploy revisions that run as the runtime SA (scoped to that SA only).
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" --project "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOYER_SA}" --role=roles/iam.serviceAccountUser >/dev/null
ok "Granted run.admin, storage.admin, artifactregistry.repoAdmin (repo), serviceAccountUser (runtime SA)"

# --------------------------------------------------------------
# 5. Workload Identity Federation
# --------------------------------------------------------------
step "5/6 Workload Identity Federation..."
if gcloud iam workload-identity-pools describe "$WIF_POOL" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  ok "Pool ${WIF_POOL} already exists"
else
  gcloud iam workload-identity-pools create "$WIF_POOL" --location=global --project "$PROJECT_ID" \
    --display-name="GitHub Actions"
  ok "Created pool ${WIF_POOL}"
fi

if gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER" \
     --workload-identity-pool="$WIF_POOL" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  ok "Provider ${WIF_PROVIDER} already exists"
else
  gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
    --workload-identity-pool="$WIF_POOL" --location=global --project "$PROJECT_ID" \
    --display-name="GitHub OIDC" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'"
  ok "Created provider ${WIF_PROVIDER} (restricted to ${GITHUB_REPO})"
fi

gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" --project "$PROJECT_ID" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/${GITHUB_REPO}" \
  >/dev/null
ok "${GITHUB_REPO} can impersonate ${DEPLOYER_SA}"

# --------------------------------------------------------------
# 6. GitHub configuration commands
# --------------------------------------------------------------
step "6/6 GitHub configuration"

# Only emit FRONTEND_URL if it is a real public URL.
GH_FRONTEND_URL=""
if [ -z "$CUSTOM_DOMAIN" ] && [ -n "$FRONTEND_URL" ] \
   && [[ "$FRONTEND_URL" != *localhost* ]] && [[ "$FRONTEND_URL" != *127.0.0.1* ]]; then
  GH_FRONTEND_URL="${FRONTEND_URL%/}"
fi

R="--repo ${GITHUB_REPO}"
echo ""
echo "======================================================"
echo "✅ GCP setup complete. Now configure GitHub."
echo "======================================================"
echo "Run these with the GitHub CLI (https://cli.github.com, 'gh auth login' first):"
echo ""
echo "# Deploy environment referenced by the workflow (add reviewers/branch rules in the UI if wanted)"
echo "gh api -X PUT repos/${GITHUB_REPO}/environments/production"
echo ""
echo "# Secrets"
echo "gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER ${R} --body '${WIF_PROVIDER_RESOURCE}'"
echo "gh secret set GCP_SERVICE_ACCOUNT ${R} --body '${DEPLOYER_SA}'"
echo ""
echo "# Variables"
echo "gh variable set GCP_PROJECT_ID ${R} --body '${PROJECT_ID}'"
if [ -n "$GOOGLE_CLIENT_ID" ]; then echo "gh variable set GOOGLE_CLIENT_ID ${R} --body '${GOOGLE_CLIENT_ID}'"; fi
if [ "$REGION" != "us-central1" ]; then echo "gh variable set GCP_REGION ${R} --body '${REGION}'"; fi
if [ "$SERVICE_NAME" != "workout-tracker" ]; then echo "gh variable set CLOUD_RUN_SERVICE ${R} --body '${SERVICE_NAME}'"; fi
if [ "$AR_REPO" != "cloud-run-source-deploy" ]; then echo "gh variable set ARTIFACT_REGISTRY_REPO ${R} --body '${AR_REPO}'"; fi
if [ "$DATABASE_NAME" != "workout_tracker" ]; then echo "gh variable set DATABASE_NAME ${R} --body '${DATABASE_NAME}'"; fi
if [ "$ALLOW_DEV_LOGIN" != "false" ]; then echo "gh variable set ALLOW_DEV_LOGIN ${R} --body '${ALLOW_DEV_LOGIN}'"; fi
if [ -n "$CUSTOM_DOMAIN" ]; then echo "gh variable set CUSTOM_DOMAIN ${R} --body '${CUSTOM_DOMAIN}'"; fi
if [ -n "$GH_FRONTEND_URL" ]; then echo "gh variable set FRONTEND_URL ${R} --body '${GH_FRONTEND_URL}'"; fi
echo ""
echo "Or set them by hand at: https://github.com/${GITHUB_REPO}/settings/secrets/actions"
echo ""
echo "Notes:"
echo "  - MONGODB_URI, JWT_SECRET and GOOGLE_CLIENT_SECRET live in Secret Manager, NOT GitHub."
echo "    To rotate one later, re-run this script after updating .env, or:"
echo "      printf '%s' 'NEW_VALUE' | gcloud secrets versions add JWT_SECRET --data-file=- --project ${PROJECT_ID}"
if $GENERATED_JWT; then echo "  - A new JWT_SECRET was generated and stored in Secret Manager (not written to .env)."; fi
echo "  - MongoDB Atlas must allow 0.0.0.0/0 in Network Access so Cloud Run can connect."
echo "======================================================"
