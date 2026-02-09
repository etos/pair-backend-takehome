import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src import api
from src.conf import AppConfig

logging.captureWarnings(True)
conf = AppConfig()

app = FastAPI(
    docs_url=conf.DOCS_URL,
    redoc_url=conf.REDOC_URL,
    openapi_url=conf.OPENAPI_URL,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.health.router)

