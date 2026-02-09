import asyncio
import logging
from enum import Enum
from fastapi import APIRouter
from fastapi.responses import JSONResponse
# from src import services as svc

logging.captureWarnings(True)
router = APIRouter()


@router.get("/api/healthz")
async def healthz():
    """K8s health check."""
    checks = {
        "postgres": "OK", #svc.postgres.check_health(),
    }
    status = 200 #if all(checks.values()) else 500
    return JSONResponse(content={"health": checks}, status_code=status)
