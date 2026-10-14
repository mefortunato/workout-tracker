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


@pytest.mark.asyncio
async def test_email_register_and_login():
    import uuid
    unique_email = f"athlete_{uuid.uuid4().hex[:8]}@example.com"
    password = "SecretPassword123!"
    name = "Test Athlete"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Register
        reg_resp = await client.post("/api/auth/register", json={
            "name": name,
            "email": unique_email,
            "password": password
        })
        assert reg_resp.status_code == 200
        reg_data = reg_resp.json()
        assert "access_token" in reg_data
        assert reg_data["user"]["email"] == unique_email
        assert reg_data["user"]["name"] == name

        # 2. Duplicate registration fails
        dup_resp = await client.post("/api/auth/register", json={
            "name": name,
            "email": unique_email,
            "password": password
        })
        assert dup_resp.status_code == 400

        # 3. Login with correct password
        login_resp = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": password
        })
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert "access_token" in login_data
        assert login_data["user"]["email"] == unique_email

        # 4. Login with incorrect password
        bad_login = await client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "WrongPassword!"
        })
        assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_challenges_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User 1 (Demo Athlete)
        login1 = await client.post("/api/auth/demo-login")
        token1 = login1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # User 2
        import uuid
        u2_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
        reg2 = await client.post("/api/auth/register", json={
            "name": "Challenger Bob",
            "email": u2_email,
            "password": "Password123!"
        })
        token2 = reg2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # 1. User 1 creates a challenge
        create_resp = await client.post("/api/challenges", headers=headers1, json={
            "title": "October 500 Push-ups",
            "description": "Reach 500 push-ups together!",
            "challenge_type": "total_volume",
            "exercise_name": "Push-ups",
            "target_value": 500,
            "start_date": "2026-10-01",
            "end_date": "2026-10-31"
        })
        assert create_resp.status_code == 201
        c_data = create_resp.json()
        assert c_data["title"] == "October 500 Push-ups"
        assert c_data["target_value"] == 500
        assert "invite_code" in c_data
        invite_code = c_data["invite_code"]
        c_id = c_data["_id"]

        # 2. User 2 joins the challenge with the invite code
        join_resp = await client.post("/api/challenges/join", headers=headers2, json={
            "invite_code": invite_code
        })
        assert join_resp.status_code == 200
        join_data = join_resp.json()
        assert join_data["participants_count"] == 2
        assert len(join_data["leaderboard"]) == 2

        # 3. User 2 logs some push-ups
        await client.post("/api/workouts/quick-log", headers=headers2, json={
            "exercise_name": "Push-ups",
            "reps": 50
        })

        # 4. View challenge details: Leaderboard should reflect User 2's progress
        detail_resp = await client.get(f"/api/challenges/{c_id}", headers=headers1)
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        leaderboard = detail_data["leaderboard"]
        assert len(leaderboard) == 2
        # Verify rank 1 has 50 completed reps
        assert leaderboard[0]["completed_reps"] >= 50

        # 5. User 2 leaves the challenge
        leave_resp = await client.post(f"/api/challenges/{c_id}/leave", headers=headers2)
        assert leave_resp.status_code == 200

        # 6. Verify participant count decreased
        after_leave = await client.get(f"/api/challenges/{c_id}", headers=headers1)
        assert after_leave.json()["participants_count"] == 1


@pytest.mark.asyncio
async def test_duration_challenge_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login user
        login = await client.post("/api/auth/demo-login")
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create challenge for Plank (duration exercise)
        create_resp = await client.post("/api/challenges", headers=headers, json={
            "title": "October Plank Endurance",
            "description": "Accumulate 30 minutes of plank this month!",
            "challenge_type": "total_volume",
            "exercise_name": "Plank",
            "target_value": 30,  # 30 minutes
            "start_date": "2026-10-01",
            "end_date": "2026-10-31"
        })
        assert create_resp.status_code == 201
        c_data = create_resp.json()
        assert c_data["target_unit"] == "minutes"
        assert c_data["target_value"] == 30
        c_id = c_data["_id"]

        # 3. Log a workout with Plank (2 sets of 60 seconds = 120s = 2 minutes)
        workout_resp = await client.post("/api/workouts", headers=headers, json={
            "title": "Core Hold Session",
            "duration_minutes": 10,
            "exercises": [
                {
                    "exercise_name": "Plank",
                    "category": "Core",
                    "type": "duration",
                    "sets": [
                        {"set_number": 1, "reps": 0, "weight": 0, "duration_seconds": 60, "completed": True},
                        {"set_number": 2, "reps": 0, "weight": 0, "duration_seconds": 60, "completed": True}
                    ],
                    "total_reps": 0,
                    "total_volume": 0
                }
            ]
        })
        assert workout_resp.status_code == 201

        # 4. Check challenge progress
        detail_resp = await client.get(f"/api/challenges/{c_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["target_unit"] == "minutes"
        user_prog = detail["user_progress"]
        assert user_prog is not None
        assert user_prog["unit"] == "minutes"
        assert user_prog["completed_reps"] >= 2  # 2 minutes completed
        assert user_prog["target_reps"] == 30
        assert user_prog["progress_percentage"] >= 6.6



