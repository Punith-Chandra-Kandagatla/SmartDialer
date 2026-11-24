from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from app.database.connection import engine
from app.api.campaigns import router as campaigns_router
from app.api.dashboard import router as dashboard_router
from app.api.dialing import router as dialing_router
from app.api.resources import router as resources_router
from app.api.events import router as events_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    engine.dispose()


app = FastAPI(
    title="SmartDialer",
    description=(
        "Intelligent outbound dialing platform "
        "with adaptive pacing and independent safety controls."
    ),
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(campaigns_router)
app.include_router(dashboard_router)
app.include_router(dialing_router)
app.include_router(resources_router)
app.include_router(events_router)

@app.get("/", tags=["General"])
def root():
    return {
        "name": "SmartDialer",
        "message": "Intelligent dialing infrastructure is running.",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Monitoring"])
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "application": "operational",
            "database": "connected"
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected"
            }
        )


@app.get("/api/v1/system/status", tags=["System"])
def system_status():
    return {
        "platform": "SmartDialer",
        "version": "1.0.0",
        "environment": "development",
        "components": {
            "progressive_dialer": "initializing",
            "predictive_engine": "initializing",
            "safety_controller": "initializing",
            "telecom_providers": "initializing"
        }
    }