from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import get_settings
from .routers import auth, loans, properties, reports, transactions

log = logging.getLogger("rentalmanager")


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    base = Path(__file__).resolve().parent.parent
    cfg = Config(str(base / "alembic.ini"))
    cfg.set_main_option("script_location", str(base / "migrations"))
    cfg.set_main_option("sqlalchemy.url", get_settings().db_url)
    command.upgrade(cfg, "head")


def create_app(migrate: bool = True) -> FastAPI:
    settings = get_settings()
    if migrate:
        run_migrations()
    app = FastAPI(title="Rental Manager", version=__version__, docs_url="/api/docs", openapi_url="/api/openapi.json")
    for r in (auth.router, auth.users_router, properties.router, transactions.router, loans.router, reports.router):
        app.include_router(r)

    @app.get("/api/health")
    def health():
        return {"ok": True, "version": __version__}

    static = settings.static_dir
    if static and Path(static).exists():
        static = Path(static)
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404)
            f = (static / path).resolve()
            if path and f.is_file() and static.resolve() in f.parents:
                return FileResponse(f)
            return FileResponse(static / "index.html")

    return app


app = create_app()
