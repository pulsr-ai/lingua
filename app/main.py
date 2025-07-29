import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.database import check_database_connection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting LLM Wrapper Service...")
    
    # Check database connection
    if not check_database_connection():
        logger.error("Database connection failed. Please check your DATABASE_URL configuration.")
        logger.error("Make sure to run database migrations: alembic upgrade head")
        raise Exception("Database connection failed")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Wrapper Service...")

app = FastAPI(
    title="LLM Wrapper Service",
    description="A unified API wrapper for various LLM providers",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )