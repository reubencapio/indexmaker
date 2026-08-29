"""
IndexMaker Web API - Main Application

A FastAPI-based web platform for building and managing custom financial indices.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Initializes resources on startup and cleans up on shutdown.
    """
    # Startup
    if settings.DEBUG:
        await init_db()
    yield
    # Shutdown (cleanup if needed)


def create_application() -> FastAPI:
    """
    Application factory pattern.

    Creates and configures the FastAPI application with all middleware,
    routes, and exception handlers.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
        # IndexMaker Web API

        Build, manage, and backtest custom financial indices.

        ## Features

        - **Index Builder**: Create custom indices with flexible weighting schemes
        - **Backtesting**: Test strategies against historical data
        - **Real-time Updates**: Track index values with live market data
        - **API Access**: Full programmatic access to all features

        ## Authentication

        Use JWT tokens for authentication. Get tokens via `/api/v1/auth/login`.
        """,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiting. Added before CORS so that CORS ends up the outer layer:
    # Starlette runs the most recently added middleware first, and a 429 emitted
    # outside CORS would reach the browser as an opaque cross-origin error.
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
            expensive_per_hour=settings.AI_RATE_LIMIT_PER_HOUR,
        )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint for load balancers and monitoring."""
        return {"status": "healthy", "version": settings.APP_VERSION}

    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/api/docs",
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle unexpected exceptions and add CORS headers to prevent misleading browser errors."""
        # An unhandled exception bypasses CORSMiddleware, so without these the
        # browser reports an opaque CORS failure instead of the real 500.
        headers = {}
        origin = request.headers.get("origin")
        if origin and ("*" in settings.CORS_ORIGINS or origin in settings.CORS_ORIGINS):
            # Echo the concrete origin: a "*" wildcard is rejected by browsers
            # whenever credentials are allowed. Allow-Methods/Allow-Headers only
            # matter on a preflight response, so they are omitted here.
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Vary"] = "Origin"

        if settings.DEBUG:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": str(exc),
                    "type": type(exc).__name__,
                },
                headers=headers,
            )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers=headers,
        )

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
