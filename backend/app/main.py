from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import __version__
from app.config import settings
from app.routers import tickets_router
from app.schemas import HealthResponse

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description="Backend API for AI Support Ticket Triage and Auto-Reply Copilot",
    docs_url="/docs",
    redoc_url="/redoc",
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

