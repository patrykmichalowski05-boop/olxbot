from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

from .models import PLATFORMS, Offer, Search, platform_url
from .parsers import LINK_PARTS, SourceError, parse_page


@dataclass(frozen=True)
class SourceConfig:
    platform: str
    mode: str = "html"
    enabled: bool = True
    feed_path: str | None = None
    storage_state_env: str | None = None
    min_interval_seconds: int = 8
    max_items: int = 100

    def __post_init__(self):
        if self.platform not in PLATFORMS or self.mode not in {
            "html",
            "browser",
            "json",
        }:
            raise ValueError("Nieprawidłowy adapter źródła")
        if type(self.enabled) is not bool:
            raise ValueError("Nieprawidłowy stan źródła")
        if (
            type(self.min_interval_seconds) is not int
            or not 3 <= self.min_interval_seconds <= 3600
        ):
            raise ValueError("Odstęp źródła musi wynosić 3–3600 sekund")
        if type(self.max_items) is not int or not 1 <= self.max_items <= 300:
            raise ValueError("Limit źródła musi wynosić 1–300")
        if self.mode == "json" and not self.feed_path:
            raise ValueError("Plik danych jest wymagany dla adaptera json")
        if self.feed_path is not None and (
            not isinstance(self.feed_path, str) or not self.feed_path.strip()
        ):
            raise ValueError("Nieprawidłowa ścieżka pliku danych")
        if self.storage_state_env is not None and (
            not isinstance(self.storage_state_env, str)
            or not self.storage_state_env.isidentifier()
        ):
            raise ValueError("Nieprawidłowa nazwa zmiennej sesji")


def search_url(platform: str, query: str) -> str:
    if platform == "OLX":
        slug = quote(query.strip().replace(" ", "-"), safe="")
        return (
            f"https://www.olx.pl/oferty/q-{slug}/?search%5Border%5D=created_at%3Adesc"
        )
    if platform == "FACEBOOK":
        return "https://www.facebook.com/marketplace/search/?" + urlencode(
            {"query": query}
        )
    if platform == "ALLEGRO_LOKALNIE":
        return "https://allegrolokalnie.pl/oferty/q/" + quote(query, safe="")
    if platform == "VINTED":
        return "https://www.vinted.pl/catalog?" + urlencode(
            {"search_text": query, "order": "newest_first"}
        )
    if platform == "OTOMOTO":
        return "https://www.otomoto.pl/osobowe?" + urlencode(
            {"search[filter_string_q]": query}
        )
    raise ValueError("Nieznana platforma")


class HttpTransport:
    def __init__(self, session=None, clock=time.monotonic, sleeper=time.sleep):
        self.session = session or requests.Session()
        self.clock, self.sleeper = clock, sleeper
        self.last = {}
        self.robots = {}
        self.user_agent = "FlipRadar/1.0"
        self.session.headers.update(
            {"User-Agent": self.user_agent, "Accept-Language": "pl-PL,pl;q=0.9"}
        )

    def _pace(self, platform: str, interval: int):
        wait = interval - (self.clock() - self.last.get(platform, -1e9))
        if wait > 0:
            self.sleeper(wait)
        self.last[platform] = self.clock()

    def _get(self, url: str, platform: str, interval: int) -> tuple[str, int]:
        for _ in range(4):
            platform_url(platform, url)
            self._pace(platform, interval)
            try:
                response = self.session.get(
                    url, timeout=(10, 25), allow_redirects=False, stream=True
                )
            except requests.RequestException:
                raise SourceError(
                    "NETWORK_ERROR", "Połączenie ze źródłem nie powiodło się"
                ) from None
            try:
                if response.status_code in (301, 302, 303, 307, 308):
                    try:
                        url = platform_url(
                            platform, urljoin(url, response.headers.get("Location", ""))
                        )
                    except ValueError:
                        raise SourceError(
                            "UNSAFE_REDIRECT",
                            "Źródło przekierowało poza dozwoloną platformę",
                        ) from None
                    continue
                if response.status_code in (401, 403):
                    raise SourceError(
                        "ACCESS_BLOCKED", "Źródło odrzuciło automatyczny dostęp"
                    )
                if response.status_code == 429:
                    raw = response.headers.get("Retry-After", "120")
                    delay = int(raw) if str(raw).isdigit() else 120
                    raise SourceError(
                        "RATE_LIMITED",
                        "Źródło ograniczyło liczbę zapytań",
                        min(max(delay, 30), 86400),
                    )
                if response.status_code >= 500:
                    raise SourceError(
                        "SOURCE_UNAVAILABLE", "Źródło jest chwilowo niedostępne"
                    )
                chunks, size = [], 0
                for chunk in response.iter_content(65536):
                    size += len(chunk)
                    if size > 6_000_000:
                        raise SourceError(
                            "RESPONSE_TOO_LARGE", "Odpowiedź źródła jest zbyt duża"
                        )
                    chunks.append(chunk)
                text = b"".join(chunks).decode(
                    response.encoding or "utf-8", errors="replace"
                )
                return text, response.status_code
            except requests.RequestException:
                raise SourceError(
                    "NETWORK_ERROR", "Odczyt odpowiedzi źródła został przerwany"
                ) from None
            finally:
                response.close()
        raise SourceError("REDIRECT_LOOP", "Zbyt wiele przekierowań źródła")

    def check_robots(self, url: str, config: SourceConfig):
        host = urlsplit(url).netloc
        cached = self.robots.get(host)
        if cached is None or cached[0] < self.clock() - 3600:
            text, status = self._get(
                f"https://{host}/robots.txt",
                config.platform,
                config.min_interval_seconds,
            )
            if status not in (200, 404):
                raise SourceError(
                    "ROBOTS_UNAVAILABLE", "Nie można sprawdzić zasad pobierania źródła"
                )
            robot = RobotFileParser()
            robot.parse(
                text.splitlines() if status == 200 else ["User-agent: *", "Allow: /"]
            )
            self.robots[host] = (self.clock(), robot)
        robot = self.robots[host][1]
        if not robot.can_fetch(self.user_agent, url):
            raise SourceError(
                "ROBOTS_DENIED",
                "Źródło nie udostępnia tej strony dla automatycznego pobierania",
            )
        delay = robot.crawl_delay(self.user_agent) or robot.crawl_delay("*")
        if delay:
            self._pace(config.platform, max(config.min_interval_seconds, delay))

    def html(self, url: str, config: SourceConfig) -> str:
        platform_url(config.platform, url)
        self.check_robots(url, config)
        text, status = self._get(url, config.platform, config.min_interval_seconds)
        if status != 200:
            raise SourceError("HTTP_ERROR", "Nie udało się pobrać listy ofert")
        return text

    def close(self):
        self.session.close()


class BrowserTransport:
    """Optional local browser session. Stops at login/CAPTCHA; never logs in."""

    def __init__(self, http: HttpTransport):
        self.http = http
        self.playwright = None
        self.browser = None
        self.contexts = {}

    def html(self, url: str, config: SourceConfig) -> str:
        state = os.getenv(config.storage_state_env or "", "")
        if config.platform == "FACEBOOK" and not state:
            raise SourceError(
                "LOGIN_REQUIRED",
                "Facebook wymaga skonfigurowanej lokalnej sesji przeglądarki",
            )
        if state and not Path(state).is_file():
            raise SourceError(
                "SESSION_MISSING", "Nie znaleziono skonfigurowanej sesji przeglądarki"
            )
        try:
            from playwright.sync_api import Error as BrowserError
            from playwright.sync_api import TimeoutError as BrowserTimeout
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SourceError(
                "BROWSER_UNAVAILABLE", "Obsługa przeglądarki nie jest zainstalowana"
            ) from None
        self.http.check_robots(url, config)
        if self.playwright is None:
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
            except (BrowserError, OSError):
                self.close()
                raise SourceError(
                    "BROWSER_UNAVAILABLE",
                    "Przeglądarka nie jest zainstalowana lub nie może zostać uruchomiona",
                ) from None
        page = None
        try:
            context = self.contexts.get(config.platform)
            if context is None:
                context = self.browser.new_context(
                    storage_state=state or None, locale="pl-PL"
                )
                context.route(
                    "**/*",
                    lambda route: (
                        route.abort()
                        if route.request.resource_type in {"image", "media", "font"}
                        else route.continue_()
                    ),
                )
                self.contexts[config.platform] = context
            page = context.new_page()
            self.http._pace(config.platform, config.min_interval_seconds)
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            platform_url(config.platform, page.url)
            if response and response.status == 429:
                raise SourceError(
                    "RATE_LIMITED", "Źródło ograniczyło liczbę zapytań", 120
                )
            if response and response.status >= 400:
                raise SourceError(
                    "ACCESS_BLOCKED", "Przeglądarka napotkała ograniczenie dostępu"
                )
            try:
                page.wait_for_selector(
                    f'a[href*="{LINK_PARTS[config.platform]}"]', timeout=10000
                )
            except BrowserTimeout:
                pass  # parse_page distinguishes an empty list from a login wall.
            for _ in range(2):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(500)
            return page.content()
        except SourceError:
            raise
        except (BrowserError, OSError, ValueError):
            raise SourceError(
                "BROWSER_ERROR", "Nie udało się odczytać listy ofert w przeglądarce"
            ) from None
        finally:
            if page:
                page.close()

    def close(self):
        for context in self.contexts.values():
            context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        self.contexts = {}
        self.browser = self.playwright = None


class SourceRegistry:
    def __init__(
        self, configs: list[SourceConfig], root: Path, http=None, browser=None
    ):
        if len({c.platform for c in configs}) != len(configs):
            raise ValueError("Platforma ma więcej niż jedną konfigurację")
        self.configs = {c.platform: c for c in configs}
        self.root = Path(root).resolve()
        self.http = http or HttpTransport()
        self.browser = browser or BrowserTransport(self.http)

    def discover(
        self, platform: str, search: Search, network: bool = False
    ) -> list[Offer]:
        config = self.configs.get(platform)
        if config is None or not config.enabled:
            raise SourceError("DISABLED", "Źródło jest wyłączone")
        if config.mode == "json":
            path = Path(config.feed_path).expanduser()
            if not path.is_absolute():
                path = self.root / path
            try:
                if path.stat().st_size > 6_000_000:
                    raise SourceError(
                        "RESPONSE_TOO_LARGE", "Plik źródłowy jest zbyt duży"
                    )
                data = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
                rows = data.get("items", data) if isinstance(data, dict) else data
                if not isinstance(rows, list) or len(rows) > 5000:
                    raise ValueError("Nieprawidłowa lista ofert")
                offers = [Offer.from_mapping(row, platform) for row in rows]
            except (OSError, ValueError, TypeError, RecursionError, ArithmeticError):
                raise SourceError(
                    "INVALID_FEED",
                    "Plik danych źródła jest niedostępny lub nieprawidłowy",
                ) from None
        else:
            if not network:
                raise SourceError(
                    "NETWORK_DISABLED", "Pobieranie sieciowe nie zostało uruchomione"
                )
            url = search.source_urls.get(platform) or search_url(platform, search.query)
            transport = self.browser if config.mode == "browser" else self.http
            offers = parse_page(transport.html(url, config), platform, url)
        return offers[: config.max_items]

    def close(self):
        self.browser.close()
        self.http.close()
