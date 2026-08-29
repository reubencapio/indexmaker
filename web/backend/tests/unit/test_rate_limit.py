"""
Unit tests for request rate limiting.

Includes the middleware-ordering property: a 429 must still carry CORS headers,
otherwise the browser reports an opaque cross-origin failure and the real cause is
invisible -- the same trap the 500 handler already had to be fixed for.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.rate_limit import RateLimitMiddleware


def _app(per_minute: int = 3, expensive_per_hour: int = 2) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/api/v1/indices")
    async def indices():
        return {"ok": True}

    @app.post("/api/v1/ai/create")
    async def ai_create():
        return {"ok": True}

    # Same order as the real application: limiter inside, CORS outside.
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=per_minute,
        expensive_per_hour=expensive_per_hour,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://www.indexmaker.ai"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


class TestGeneralLimit:
    def test_requests_under_the_limit_pass(self):
        client = TestClient(_app(per_minute=3))
        for _ in range(3):
            assert client.get("/api/v1/indices").status_code == 200

    def test_request_over_the_limit_is_rejected(self):
        client = TestClient(_app(per_minute=3))
        for _ in range(3):
            client.get("/api/v1/indices")
        response = client.get("/api/v1/indices")
        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_clients_have_separate_budgets(self):
        client = TestClient(_app(per_minute=2))
        for _ in range(2):
            client.get("/api/v1/indices", headers={"X-Forwarded-For": "1.1.1.1"})

        blocked = client.get("/api/v1/indices", headers={"X-Forwarded-For": "1.1.1.1"})
        other = client.get("/api/v1/indices", headers={"X-Forwarded-For": "2.2.2.2"})

        assert blocked.status_code == 429
        assert other.status_code == 200


class TestExemptions:
    def test_health_is_never_limited(self):
        """The platform cycles the instance if health checks start failing."""
        client = TestClient(_app(per_minute=1))
        for _ in range(10):
            assert client.get("/health").status_code == 200

    def test_preflight_is_never_limited(self):
        client = TestClient(_app(per_minute=1))
        headers = {
            "Origin": "https://www.indexmaker.ai",
            "Access-Control-Request-Method": "GET",
        }
        for _ in range(10):
            assert client.options("/api/v1/indices", headers=headers).status_code == 200


class TestExpensiveEndpoints:
    def test_ai_endpoints_have_a_tighter_budget(self):
        client = TestClient(_app(per_minute=100, expensive_per_hour=2))
        for _ in range(2):
            assert client.post("/api/v1/ai/create").status_code == 200
        assert client.post("/api/v1/ai/create").status_code == 429

    def test_the_ai_budget_does_not_limit_ordinary_reads(self):
        client = TestClient(_app(per_minute=100, expensive_per_hour=1))
        client.post("/api/v1/ai/create")
        client.post("/api/v1/ai/create")  # exhausted
        assert client.get("/api/v1/indices").status_code == 200


class TestCorsInteraction:
    def test_a_429_still_carries_cors_headers(self):
        """Without this the browser shows a CORS error instead of the rate limit."""
        client = TestClient(_app(per_minute=1))
        origin = {"Origin": "https://www.indexmaker.ai"}

        client.get("/api/v1/indices", headers=origin)
        blocked = client.get("/api/v1/indices", headers=origin)

        assert blocked.status_code == 429
        assert blocked.headers["access-control-allow-origin"] == "https://www.indexmaker.ai"
