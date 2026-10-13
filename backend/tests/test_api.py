import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, close_db


@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def setup_test_db():
    await init_db()
    yield
    await close_db()


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["app"] == "Workout Tracker"


@pytest.mark.asyncio
async def test_auth_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "google_auth_enabled" in data
        assert "dev_login_enabled" in data


@pytest.mark.asyncio
async def test_demo_login_and_me():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Perform demo login
        login_resp = await client.post("/api/auth/demo-login")
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert "access_token" in data
        token = data["access_token"]
        assert data["user"]["email"] == "athlete@workout-tracker.app"

        # Check /api/auth/me with Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await client.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "athlete@workout-tracker.app"


@pytest.mark.asyncio
async def test_quick_log_and_workouts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Login
        login_resp = await client.post("/api/auth/demo-login")
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Quick log 25 push-ups
        quick_resp = await client.post(
            "/api/workouts/quick-log",
            json={"exercise_name": "Push-ups", "reps": 25, "weight": 0.0},
            headers=headers
        )
        assert quick_resp.status_code == 200
        workout = quick_resp.json()
        assert any(ex["exercise_name"] == "Push-ups" for ex in workout["exercises"])

        # Quick log 30 sit-ups
        quick_resp2 = await client.post(
            "/api/workouts/quick-log",
            json={"exercise_name": "Sit-ups", "reps": 30, "weight": 0.0},
            headers=headers
        )
        assert quick_resp2.status_code == 200
        workout2 = quick_resp2.json()
        assert any(ex["exercise_name"] == "Sit-ups" for ex in workout2["exercises"])

        # List workouts
        list_resp = await client.get("/api/workouts", headers=headers)
        assert list_resp.status_code == 200
        workouts = list_resp.json()
        assert len(workouts) >= 1


@pytest.mark.asyncio
async def test_stats_and_prs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post("/api/auth/demo-login")
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Summary stats
        summary_resp = await client.get("/api/stats/summary", headers=headers)
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert "total_pushups" in summary
        assert "total_situps" in summary
        assert "current_streak_days" in summary

        # Personal records
        prs_resp = await client.get("/api/stats/prs", headers=headers)
        assert prs_resp.status_code == 200
        prs = prs_resp.json()
        assert isinstance(prs, list)

        # Chart data
        chart_resp = await client.get("/api/stats/chart-data?days=7", headers=headers)
        assert chart_resp.status_code == 200
        chart_data = chart_resp.json()
        assert len(chart_data) >= 7


@pytest.mark.asyncio
async def test_exercises_and_goals():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post("/api/auth/demo-login")
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List exercises
        ex_resp = await client.get("/api/exercises", headers=headers)
        assert ex_resp.status_code == 200
        exercises = ex_resp.json()
        assert len(exercises) >= 5

        # Create custom exercise
        custom_ex_resp = await client.post(
            "/api/exercises",
            json={
                "name": "Diamond Push-ups",
                "category": "Upper Body",
                "type": "reps",
                "description": "Close hand diamond placement push-up."
            },
            headers=headers
        )
        assert custom_ex_resp.status_code in (200, 201, 400)

        # List goals
        goals_resp = await client.get("/api/goals", headers=headers)
        assert goals_resp.status_code == 200
        goals = goals_resp.json()
        assert isinstance(goals, list)


@pytest.mark.asyncio
async def test_static_html_and_asset_serving():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Root index.html
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "html" in resp.headers["content-type"]
        assert "PULSE" in resp.text or "Workout" in resp.text

        # Workouts page
        resp_w = await client.get("/workouts")
        assert resp_w.status_code == 200
        assert "html" in resp_w.headers["content-type"]

        # Stats page
        resp_s = await client.get("/stats")
        assert resp_s.status_code == 200
        assert "html" in resp_s.headers["content-type"]

        # Login page
        resp_l = await client.get("/login")
        assert resp_l.status_code == 200
        assert "html" in resp_l.headers["content-type"]

