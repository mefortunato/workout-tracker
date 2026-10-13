# ⚡ PulseFit — Full-Stack Workout & Reps Tracker

A high-performance full-stack workout tracking application built with **SvelteKit** (compiled to static HTML), **FastAPI**, **MongoDB**, **uv**, and **Docker**.

Track push-ups, sit-ups, pull-ups, squats, and custom routines with one-tap quick logging, personal record (PR) tracking, consistency streak counters, interactive analytics charts, and **Google Sign-In**.

---

## 🌟 Key Features

- **⚡ Frictionless Rep Tracking**: One-tap quick logging buttons (`+10`, `+25`, `+50`) for push-ups, sit-ups, pull-ups, squats, or custom reps.
- **🏋️ Full Workout Session Logger**: Record multi-set workouts with weights (kg/lbs), timed holds (planks), exercise categories, and session notes.
- **🎯 Dynamic Goals & Targets**: Create daily or weekly rep/workout goals with animated progress rings, percent completion badges, and one-click boost buttons.
- **📈 Rich Analytics & Interactive Charts**: Time-series volume distribution charts, lifetime workout metrics, and all-time Personal Records (PRs) per movement.
- **🔥 Streak & Consistency Counter**: Dynamic daily streak calculations and milestone celebration indicators.
- **🔑 Google OAuth 2.0 & Instant Demo Mode**: Seamless Sign In with Google (via Google Identity Services and OAuth2 authorization code flow) plus a zero-configuration 1-click Demo mode for local testing.
- **📦 Single-Container Unified Architecture**: SvelteKit is pre-rendered to optimized static HTML/SPA files and served directly by FastAPI alongside the REST API.
- **🚀 Python Packaging via `uv`**: Ultra-fast dependency resolution and deterministic virtual environments.

---

## 🛠️ Technology Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | [SvelteKit](https://svelte.dev/) (Svelte 5) | Component-driven UI using `@sveltejs/adapter-static` for static HTML export |
| **Styling** | Vanilla CSS Design System | Custom athletic dark-mode theme, glassmorphic cards, micro-animations |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) | Async Python 3.11+ web framework with OpenAPI `/docs` |
| **Database** | [MongoDB](https://www.mongodb.com/) + Motor | Async MongoDB driver with auto-indexing and exercise seeding |
| **Auth** | Google OAuth2 + JWT | Google Identity Services token verification and secure JWT sessions |
| **Python Tooling**| [Astral `uv`](https://astral.sh/uv) | Modern, blazing-fast Python package and project manager |
| **Containerization**| Docker & Docker Compose | Multi-stage Dockerfile packaging static frontend, backend, and MongoDB |

---

## 📁 Project Structure

```
workout-tracker/
├── backend/
│   ├── app/
│   │   ├── config.py             # Settings (pydantic-settings, environment variables)
│   │   ├── database.py           # Async Motor MongoDB connection & index initializer
│   │   ├── main.py               # FastAPI app, API routers & static SPA fallback
│   │   ├── models/               # Pydantic schemas (User, Workout, Exercise, Goal)
│   │   ├── routers/              # API Endpoints (auth, workouts, exercises, stats, goals)
│   │   ├── services/             # Auth service & Google token verification
│   │   ├── utils/                # Auth dependencies & UTC date helpers
│   │   └── static/               # Built SvelteKit static site (generated)
│   ├── tests/                    # Pytest test suite (health, auth, workouts, stats)
│   ├── pyproject.toml            # uv project definition & dependencies
│   └── uv.lock                   # Deterministic dependency lockfile
├── frontend/
│   ├── src/
│   │   ├── app.html              # HTML shell with Google Fonts & Google Identity script
│   │   ├── app.css               # Bespoke Vanilla CSS athletic design system
│   │   ├── lib/
│   │   │   ├── api.ts            # Typed client API client
│   │   │   ├── stores.ts         # User auth store & toast notifications
│   │   │   ├── types.ts          # TypeScript interfaces
│   │   │   └── components/       # UI components (Navbar, Modals, StatsChart, Cards)
│   │   └── routes/
│   │       ├── +layout.svelte    # Shell layout with navigation & toast container
│   │       ├── +layout.ts        # SPA prerender configuration
│   │       ├── +page.svelte      # Main Dashboard & Quick Log Station
│   │       ├── workouts/         # Workout session history & logs
│   │       ├── exercises/        # Movement directory & custom exercise creator
│   │       ├── goals/            # Target benchmarks & progress tracking
│   │       ├── stats/            # Analytics charts, volume trends & PRs
│   │       └── login/            # Google Sign In & instant demo login
│   ├── svelte.config.js
│   ├── vite.config.ts            # Configured with @sveltejs/adapter-static
│   └── package.json
├── Dockerfile                    # Multi-stage build (Node builder + uv Python runner)
├── docker-compose.yml            # App (port 8080) + MongoDB (port 27018)
├── .env.example                  # Environment configuration template
└── README.md
```

---

## 🚀 Quick Start with Docker (Recommended)

To run the entire application with Docker Compose:

1. **Clone and navigate to the directory**:
   ```bash
   cd /home/mfort/projects/workout-tracker
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```

3. **Start the containers**:
   ```bash
   docker compose up --build
   ```

4. **Access the Application**:
   - **Workout Tracker Web App**: [http://localhost:8080](http://localhost:8080)
   - **Interactive API Documentation (Swagger)**: [http://localhost:8080/docs](http://localhost:8080/docs)
   - **API Health Check**: [http://localhost:8080/api/health](http://localhost:8080/api/health)

---

## 💻 Local Development Setup

### Quick Start (One Command)
Run both backend and frontend development servers with live reload connected to local MongoDB:
```bash
./scripts/dev.sh
```
*This automatically starts the local MongoDB container (port 27018), overrides `MONGODB_URI` to use local MongoDB instead of production Atlas, and launches FastAPI (`http://127.0.0.1:8000`) and the Vite dev server (`http://localhost:5173`).*

---

### Manual Setup (Step-by-Step)
- Node.js 22+ & npm
- Python 3.11+
- Astral `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Local MongoDB running on `localhost:27018`

#### 1. Backend Setup
```bash
cd backend

# Install all dependencies with uv
uv sync --all-extras

# Run the test suite
uv run pytest tests/

# Start FastAPI development server
uv run uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install npm packages
npm install

# Start Vite development server (proxies /api to localhost:8000)
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 3. Build Static Frontend for FastAPI Serving
```bash
cd frontend
npm run build
```
This builds the static HTML, CSS, and JS into `backend/app/static`, allowing FastAPI at `http://localhost:8000` to serve the complete application autonomously!

---

## 🔑 Google OAuth 2.0 Setup Guide

To enable live Sign-In with your real Google account:

1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `workout-tracker`).
3. Navigate to **APIs & Services** > **OAuth consent screen**:
   - Choose **External** (or Internal for Google Workspace).
   - Enter App name (`PulseFit Workout Tracker`) and developer contact email.
   - Save and proceed.
4. Navigate to **APIs & Services** > **Credentials**:
   - Click **Create Credentials** > **OAuth client ID**.
   - Select **Web application**.
   - Under **Authorized JavaScript origins**, add:
     - `http://localhost:8080` (Docker app)
     - `http://localhost:5173` (Vite dev server)
     - `http://localhost:8000` (FastAPI local server)
   - Under **Authorized redirect URIs**, add:
     - `http://localhost:8080/api/auth/google/callback`
     - `http://localhost:8000/api/auth/google/callback`
5. Copy the generated **Client ID** and **Client Secret** into your `.env` file:
   ```env
   GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   ```
6. Restart the app. The Google Sign-In button will activate automatically.

---

## 🧪 Testing

The backend includes comprehensive async test coverage testing all endpoints:
```bash
cd backend
uv run pytest tests/
```
Output:
```
tests/test_api.py::test_health_endpoint PASSED
tests/test_api.py::test_auth_config PASSED
tests/test_api.py::test_demo_login_and_me PASSED
tests/test_api.py::test_quick_log_and_workouts PASSED
tests/test_api.py::test_stats_and_prs PASSED
tests/test_api.py::test_exercises_and_goals PASSED
tests/test_api.py::test_static_html_and_asset_serving PASSED
=========================== 7 passed in 0.68s ============================
```

---

## ☁️ Google Cloud Deployment (Cloud Run)

The application is packaged as a single self-contained multi-stage Docker container (SvelteKit static build + FastAPI + Uvicorn) designed for **Google Cloud Run**.

### Prerequisites
1. **Google Cloud Project**: You already have one set up for Google OAuth.
2. **MongoDB Atlas**:
   - Go to [MongoDB Atlas](https://cloud.mongodb.com/)
   - Under **Security** > **Network Access** > **IP Access List**:
     - Click **Add IP Address** -> Select **Allow Access From Anywhere** (`0.0.0.0/0`) so Google Cloud Run's dynamic IP addresses can connect.
   - Verify your database connection string in `.env`:
     ```env
     MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
     DATABASE_NAME=workout_tracker
     ```

### Method 1: Using the Automated Script (`gcloud` CLI)

1. If you haven't installed the `gcloud` CLI yet:
   ```bash
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. Set your active project:
   ```bash
   gcloud config set project YOUR_GCP_PROJECT_ID
   ```

3. Run the automated deployment script:
   ```bash
   ./scripts/deploy-gcp.sh
   ```

This will automatically:
- Enable Cloud Run and Cloud Build APIs
- Build the container using Cloud Build (no local Docker daemon required)
- Deploy to Cloud Run with auto-scaling (scales to 0 when idle to minimize costs)
- Provide your live HTTPS URL (e.g. `https://workout-tracker-xyz-uc.a.run.app`)

---

### Method 2: Deploying via Google Cloud Console (Web UI)

1. **Push your code to GitHub** (or Cloud Source Repositories).
2. Go to [Google Cloud Run Console](https://console.cloud.google.com/run).
3. Click **Create Service**.
4. Select **Continuously deploy from a repository** (or Build using Dockerfile).
5. Configure service settings:
   - **Service name**: `workout-tracker`
   - **Region**: `us-central1` (or your preferred region)
   - **Authentication**: Allow unauthenticated invocations (public access)
   - **Container port**: `8080` (or leave default, our Dockerfile automatically detects `$PORT`)
6. Under **Variables & Secrets**, add your environment variables from `.env`:
   - `MONGODB_URI`
   - `DATABASE_NAME`
   - `JWT_SECRET`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `ALLOW_DEV_LOGIN`: `true`
7. Click **Create**. Cloud Run will build and deploy your container!

---

### Final Step: Update OAuth Redirects
The automated deployment script (`./scripts/deploy-gcp.sh`) automatically configures `FRONTEND_URL` on Cloud Run using the values specified in your `.env` or environment variables (e.g. `FRONTEND_URL` or `CUSTOM_DOMAIN`).

To ensure Google Sign-In operates smoothly, in [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials):
1. Select your **OAuth 2.0 Client ID** (Web application)
2. Under **Authorized JavaScript origins**, add:
   - `https://YOUR_CUSTOM_DOMAIN.com` (if using a custom domain)
   - `https://YOUR_SERVICE_URL.run.app`
3. Under **Authorized redirect URIs**, add:
   - `https://YOUR_CUSTOM_DOMAIN.com/api/auth/google/callback` (if using a custom domain)
   - `https://YOUR_SERVICE_URL.run.app/api/auth/google/callback`

