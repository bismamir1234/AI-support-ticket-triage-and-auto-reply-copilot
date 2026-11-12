from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app import __version__
from app.config import settings
from app.database import ensure_sqlite_schema
from app.routers import tickets_router
from app.schemas import HealthResponse
from app.services.exceptions import AIServiceError

# Ensure SQLite schema is up-to-date on startup
ensure_sqlite_schema()

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description="Backend API for AI Support Ticket Triage and Auto-Reply Copilot",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(AIServiceError)
async def ai_service_exception_handler(_request: Request, exc: AIServiceError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.user_message,
            "error_code": exc.error_code,
        },
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(tickets_router)


@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        version=__version__,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)

