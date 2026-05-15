from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.reports_output_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.charts_output_dir).mkdir(parents=True, exist_ok=True)
    Path("/data").mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    await engine.dispose()


def create_app() -> FastAPI:
    setup_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": settings.app_name}

    app.include_router(api_router, prefix=settings.api_prefix)

    static_path = Path(settings.static_dir or "/app/static")
    if static_path.exists():
        app.mount("/_next", StaticFiles(directory=static_path / "_next"), name="next-static")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            if full_path.startswith("api"):
                return {"detail": "Not Found"}
            candidates = [
                static_path / full_path,
                static_path / f"{full_path}.html",
                static_path / full_path / "index.html",
            ]
            for file_path in candidates:
                if file_path.is_file():
                    return FileResponse(file_path)
            index = static_path / "index.html"
            if index.exists():
                return FileResponse(index)
            return {"detail": "Frontend not built"}

    return app


app = create_app()
