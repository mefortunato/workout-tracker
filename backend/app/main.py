import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db
from app.routers import auth, workouts, exercises, stats, goals, challenges

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("workout_tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and indexes
    await init_db()
    yield
    # Shutdown
    await close_db()


# Interactive API docs are handy locally but needlessly map the attack surface in production.
_docs_enabled = not settings.is_production

app = FastAPI(
    title=settings.APP_NAME,
    description="Full stack Workout Tracker backend with MongoDB, Google OAuth, and SvelteKit static serving.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin-allow-popups")
    if settings.cookie_secure:
        headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/"):
        # API responses carry personal data; keep them out of shared caches.
        headers.setdefault("Cache-Control", "no-store")
    return response

# Include API routers
app.include_router(auth.router)
app.include_router(workouts.router)
app.include_router(exercises.router)
app.include_router(stats.router)
app.include_router(goals.router)
app.include_router(challenges.router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
    }


# Static file serving & Single Page Application (SPA) fallback
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = (BASE_DIR / "static").resolve()


def _safe_static_file(relative_path: str) -> Optional[Path]:
    """Resolves a request path inside STATIC_DIR, refusing anything that escapes it.

    Without this check `GET /%2Fetc%2Fpasswd` or `GET /..%2Fconfig.py` would read
    arbitrary files (e.g. /proc/self/environ, which holds JWT_SECRET and DB credentials).
    """
    if not relative_path or "\x00" in relative_path:
        return None
    try:
        candidate = (STATIC_DIR / relative_path.lstrip("/")).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(STATIC_DIR) or not candidate.is_file():
        return None
    return candidate

# Mount _app directory directly if it exists for SvelteKit static chunks
app_dir = STATIC_DIR / "_app"
if app_dir.exists():
    app.mount("/_app", StaticFiles(directory=str(app_dir)), name="_app")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    # Don't intercept API routes that 404
    if full_path.startswith("api/"):
        return Response(status_code=404, content='{"detail":"Not Found"}', media_type="application/json")

    # Check if a specific static file was requested (e.g. favicon.png, robots.txt)
    requested_file = _safe_static_file(full_path)
    if requested_file:
        return FileResponse(requested_file)

    # Check if a prerendered route.html exists (e.g. workouts.html, stats.html)
    clean_path = full_path.rstrip("/")
    if clean_path:
        html_file = _safe_static_file(f"{clean_path}.html")
        if html_file:
            return FileResponse(html_file)

    # Otherwise serve index.html for SvelteKit client-side routing
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    # Fallback if frontend is not yet built
    return HTMLResponse(
        """<!DOCTYPE html>
        <html>
        <head><title>Workout Tracker</title></head>
        <body style="font-family: system-ui; background: #0f172a; color: #f8fafc; padding: 3rem; text-align: center;">
            <h1 style="color: #10b981;">Workout Tracker API is Running!</h1>
            <p>The backend is active. Run <code>npm run build</code> in the frontend folder to build the SvelteKit static site.</p>
            <p><a href="/docs" style="color: #38bdf8; font-weight: bold;">View Interactive API Documentation (/docs)</a></p>
        </body>
        </html>"""
    )
