import pytest

from app.utils.security import auth_limiter, join_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Tests share one client IP, so keep the per-IP limiters from tripping between tests."""
    auth_limiter.reset()
    join_limiter.reset()
    yield
    auth_limiter.reset()
    join_limiter.reset()
