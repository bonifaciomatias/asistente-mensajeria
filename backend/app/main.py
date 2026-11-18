from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, ingest

app = FastAPI(title="Asistente Mensajería")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # desarrollo; restringir en producción
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ingest.router)