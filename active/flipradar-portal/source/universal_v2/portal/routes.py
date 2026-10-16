from __future__ import annotations

import os
import sqlite3

from fastapi import Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from flip_core.auth_store import LoginRateLimited

from .plans import PLANS, PUBLIC_PLANS
from .store import AccessDenied

SESSION_COOKIE = "flipradar_session"
GUEST_COOKIE = "flipradar_guest"


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=1, max_length=512)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=3, max_length=120)
    operation: str = Field(pattern=r"^[A-Za-z0-9_.:-]{8,120}$")


class PlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: str = Field(pattern=r"^(STANDARD|PLUS)$")


class AdminRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str = Field(min_length=1, max_length=120)
    operation: str = Field(pattern=r"^[A-Za-z0-9_.:-]{8,120}$")
    action: str = Field(pattern=r"^(activate|disable)$")
    plan: str | None = Field(default=None, pattern=r"^(START|STANDARD|PLUS)$")


def attach(app, portal, auth):
    secure = os.getenv("FLIP_PORTAL_COOKIE_SECURE", "1") != "0"
    session_cookie = "__Host-" + SESSION_COOKIE if secure else SESSION_COOKIE + "_dev"
    guest_cookie = "__Host-" + GUEST_COOKIE if secure else GUEST_COOKIE + "_dev"
    public_owner = os.getenv("FLIP_PORTAL_PUBLIC_SEARCH_OWNER_ID", "").strip()
    public_demo = os.getenv("FLIP_PORTAL_PUBLIC_DATA_IS_DEMO") == "1"
    registration = os.getenv("FLIP_PORTAL_OPEN_REGISTRATION", "1") == "1"
    allowed_origins = {
        value.strip().rstrip("/")
        for value in os.getenv("FLIP_PORTAL_ALLOWED_ORIGINS", "").split(",")
        if value.strip()
    }

    @app.exception_handler(AccessDenied)
    async def access_error(request, error):
        return JSONResponse(
            {"detail": str(error), "code": error.code}, status_code=error.status
        )

    def identity(authorization: str | None = Header(default=None)):
        parts = (authorization or "").split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(401, "Unauthorized")
        try:
            return auth.verify_access(parts[1])
        except (ValueError, sqlite3.Error):
            raise HTTPException(401, "Unauthorized") from None

    def csrf(request: Request):
        if request.headers.get("X-FlipRadar-Client") != "portal":
            raise HTTPException(403, "Odśwież stronę i spróbuj ponownie.")
        origin = request.headers.get("origin")
        current = str(request.base_url).rstrip("/")
        if request.headers.get("sec-fetch-site") == "cross-site" or (
            origin and origin.rstrip("/") not in allowed_origins | {current}
        ):
            raise HTTPException(403, "Niedozwolone źródło żądania.")

    def ip(request):
        # Proxy headers are trusted only through the ASGI server's explicit
        # trusted-proxy configuration, never directly from an arbitrary header.
        return portal.ip_key(request.client.host if request.client else "unknown")

    def cookie(response, name, value, seconds):
        response.set_cookie(
            name,
            value,
            max_age=seconds,
            httponly=True,
            secure=secure,
            samesite="lax",
            path="/",
        )

    @app.middleware("http")
    async def protect_bot(request: Request, call_next):
        path = request.url.path
        protected = (
            path.startswith("/api/v1/universal/")
            or path == "/api/v1/radar"
            or path.startswith("/api/v1/listings")
            or path.startswith("/api/v2/")
        )
        if protected:
            header = request.headers.get("authorization", "").split(" ", 1)
            if len(header) == 2 and header[0].lower() == "bearer":
                try:
                    user_id = auth.verify_access(header[1])
                except (ValueError, sqlite3.Error):
                    return await call_next(request)
                try:
                    account = portal.require_bot(user_id)
                    if (
                        path == "/api/v1/radar" or path.startswith("/api/v1/listings")
                    ) and account["plan"]["code"] != "LEGACY":
                        raise AccessDenied(
                            "PRIVATE_RADAR_REQUIRED",
                            "Użyj radaru przypisanego do swojego konta.",
                            403,
                        )
                except AccessDenied as error:
                    return JSONResponse(
                        {"detail": str(error), "code": error.code},
                        status_code=error.status,
                    )
        return await call_next(request)

    @app.get("/api/v1/public/config")
    def config():
        return {
            "name": "FlipRadar",
            "plans": [PLANS[key].payload() for key in PUBLIC_PLANS],
            "free_guest_searches": 3,
            "registration_enabled": registration,
            "public_search_available": bool(public_owner),
            "demo_data": public_demo,
            "payment_mode": "MANUAL_ACTIVATION",
        }

    @app.post("/api/v1/portal/auth/register", dependencies=[Depends(csrf)])
    def register(data: Credentials, request: Request, response: Response):
        if not registration:
            raise HTTPException(403, "Rejestracja jest obecnie wstrzymana.")
        portal.rate_limit("registration", ip(request), 5, 3600)
        try:
            user = portal.register(data.username, data.password)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
        tokens = auth.login(data.username.strip().lower(), data.password)
        portal.logout_browser(request.cookies.get(session_cookie))
        cookie(
            response,
            session_cookie,
            portal.create_browser_session(user, tokens["access_token"]),
            7 * 86400,
        )
        return tokens

    @app.post("/api/v1/portal/auth/login", dependencies=[Depends(csrf)])
    def login(data: Credentials, request: Request, response: Response):
        portal.rate_limit("login", ip(request), 30, 900)
        try:
            tokens = auth.login(portal.login_name(data.username), data.password)
        except LoginRateLimited as error:
            raise HTTPException(
                429,
                "Zbyt wiele prób. Spróbuj ponownie później.",
                headers={"Retry-After": str(error.retry_after)},
            ) from None
        except ValueError:
            raise HTTPException(401, "Nieprawidłowy login lub hasło.") from None
        user = auth.verify_access(tokens["access_token"])
        portal.account(user)
        portal.logout_browser(request.cookies.get(session_cookie))
        cookie(
            response,
            session_cookie,
            portal.create_browser_session(user, tokens["access_token"]),
            7 * 86400,
        )
        return tokens

    @app.post("/api/v1/portal/auth/resume", dependencies=[Depends(csrf)])
    def resume(request: Request):
        portal.rate_limit("resume", ip(request), 60, 60)
        return portal.resume_browser(request.cookies.get(session_cookie))

    @app.post("/api/v1/portal/auth/logout", dependencies=[Depends(csrf)])
    def logout(request: Request, response: Response):
        parts = request.headers.get("authorization", "").split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            portal.logout_access(parts[1])
        portal.logout_browser(request.cookies.get(session_cookie))
        response.delete_cookie(
            session_cookie, path="/", secure=secure, httponly=True, samesite="lax"
        )
        return {"ok": True}

    @app.get("/api/v1/portal/me")
    def account(user_id: str = Depends(identity)):
        return portal.account(user_id)

    @app.post("/api/v1/portal/plan-requests")
    def request_plan(data: PlanRequest, user_id: str = Depends(identity)):
        return portal.request_plan(user_id, data.plan)

    @app.get("/api/v1/portal/admin")
    def admin(user_id: str = Depends(identity)):
        return portal.admin_list(user_id)

    @app.post("/api/v1/portal/admin/access")
    def admin_access(data: AdminRequest, user_id: str = Depends(identity)):
        try:
            return portal.admin_access(
                user_id, data.operation, data.user_id, data.action, data.plan
            )
        except AccessDenied:
            raise
        except ValueError as error:
            raise HTTPException(422, str(error)) from None

    @app.get("/api/v1/portal/notifications")
    def notifications(
        before_id: int | None = Query(default=None, gt=0),
        user_id: str = Depends(identity),
    ):
        return portal.inbox(user_id, before_id)

    @app.post("/api/v1/public/search", dependencies=[Depends(csrf)])
    def search(data: SearchRequest, request: Request, response: Response):
        query = data.query.strip()
        if len(query) < 3:
            raise HTTPException(422, "Wpisz co najmniej 3 znaki.")
        if not public_owner:
            raise HTTPException(
                503,
                "Porównania cen nie są jeszcze udostępnione. Możesz przejść do własnego radaru.",
            )
        authorization = request.headers.get("authorization")
        user = identity(authorization) if authorization else None
        portal.rate_limit("public-search", ip(request), 30, 60)

        def lookup(value):
            # The owner ID is configured explicitly by the operator, never
            # accepted from a public request. No personal profiles are exposed.
            items = portal.store.radar(public_owner, query=value, limit=8)["items"]
            return [
                {
                    **item,
                    "valuation": {
                        key: value
                        for key, value in item["valuation"].items()
                        if key
                        in {
                            "market",
                            "confidence",
                            "image_url",
                            "category",
                            "quick_sale",
                        }
                    },
                }
                for item in items
            ]

        result, guest = portal.search(
            query,
            data.operation,
            lookup,
            user,
            request.cookies.get(guest_cookie),
            ip(request),
        )
        if guest:
            cookie(response, guest_cookie, guest, 86400)
        result["example"] = public_demo
        return result
