"""Reuse existing bearer sessions; enforce workspace roles."""

import sqlite3
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from flip_core.auth_store import AuthStore
from backend.app.db.models import Membership


class WorkspaceSecurity:

    def __init__(self, auth_db):
        path = Path(auth_db).resolve()
        prod = Path("/opt/olx-bot")

        if (
            path == prod
            or prod in path.parents
            or not path.is_file()
        ):
            raise RuntimeError(
                "Only existing isolated auth DB permitted"
            )

        self.auth = AuthStore(path)

    def current_user(self, authorization):
        pieces = (authorization or "").split(" ", 1)

        if (
            len(pieces) != 2
            or pieces[0].lower() != "bearer"
        ):
            raise HTTPException(
                401,
                "Unauthorized",
            )

        try:
            return self.auth.verify_access(pieces[1])

        except (ValueError, sqlite3.Error):
            raise HTTPException(
                401,
                "Unauthorized",
            ) from None

    @staticmethod
    def require_role(
        session,
        workspace_id,
        user_id,
        *,
        write=False,
    ):
        role = session.scalar(
            select(Membership.role).where(
                Membership.workspace_id == workspace_id,
                Membership.user_id == user_id,
            )
        )

        if role not in ("owner", "admin", "member"):
            raise HTTPException(
                403,
                "Workspace access denied",
            )

        if write and role not in ("owner", "admin"):
            raise HTTPException(
                403,
                "Write permission denied",
            )

        return role
