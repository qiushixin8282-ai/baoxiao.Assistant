"""FastAPI 应用入口。"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import (
    approval,
    audit,
    chat,
    combination,
    health,
    invoices,
    ledger,
    rules,
    system,
    workspaces,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title=settings.app_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(combination.router, prefix="/api")
app.include_router(ledger.router, prefix="/api")
app.include_router(approval.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

if settings.web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(settings.web_dir)), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(settings.web_dir / "index.html")

    @app.get("/demo", include_in_schema=False)
    def demo() -> FileResponse:
        return FileResponse(settings.web_dir / "demo.html")
