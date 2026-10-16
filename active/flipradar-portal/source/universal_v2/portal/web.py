"""Serve the Expo web export and API on one origin; no browser-token handoff."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse

from universal_v2.mobile_bridge import create_app as create_api


def create_app():
    root = (
        Path(os.environ.get("FLIP_PORTAL_WEB_ROOT", "mobile/dist"))
        .expanduser()
        .resolve()
    )
    if not (root / "index.html").is_file():
        raise RuntimeError(
            "Najpierw wykonaj eksport web aplikacji i wskaż FLIP_PORTAL_WEB_ROOT"
        )
    app = create_api()
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not found")
        if any(part.startswith(".") for part in Path(path).parts) or Path(
            path
        ).suffix in {
            ".env",
            ".db",
            ".sqlite",
            ".sqlite3",
            ".pem",
            ".key",
            ".py",
            ".sh",
        }:
            raise HTTPException(404, "Not found")
        target = (root / path).resolve()
        if not target.is_relative_to(root):
            raise HTTPException(404, "Not found")
        choices = [target, Path(str(target) + ".html"), target / "index.html"]
        for candidate in choices:
            if candidate.is_file() and candidate.resolve().is_relative_to(root):
                return FileResponse(candidate)
        # Client routing handles dynamic /offer/:id and /flips/:id routes.
        if (
            path
            and path.split("/")[0] in {"offer", "purchase", "flips"}
            and "." not in path
        ):
            return FileResponse(root / "index.html")
        raise HTTPException(404, "Nie znaleziono strony")

    return app
