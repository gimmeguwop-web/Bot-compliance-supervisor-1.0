"""
FastAPI application entry point.

Configures middleware, routers, and startup/shutdown events.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.logging import get_logging_config, get_logger
from app.db.session import create_db_and_tables
from app.api import documents, tasks, reports

logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("Starting ESKD Validator API", env=settings.APP_ENV)
    get_logging_config(settings.LOG_LEVEL)
    
    # Create database tables
    create_db_and_tables()
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ESKD Validator API")


app = FastAPI(
    title="ESKD Validator API",
    description="Production-ready system for batch validation of engineering documentation against ESKD and GOST standards.",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "ESKD Validator API",
        "docs": "/docs",
        "version": "0.1.0"
    }
