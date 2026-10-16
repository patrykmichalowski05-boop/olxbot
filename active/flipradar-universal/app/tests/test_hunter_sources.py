import json

import pytest
from test_hunter_pricing import search

from examples.generate_hunter_demo import demo_url
from universal_v2.hunter.models import PLATFORMS
from universal_v2.hunter.parsers import SourceError, parse_page
from universal_v2.hunter.sources import (
    HttpTransport,
    SourceConfig,
    SourceRegistry,
    search_url,
)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_html_card_for_every_platform(platform):
    url = demo_url(platform, "123456789")
    html = f'<article data-cy="l-card" data-testid="listing-ad" data-id="1"><a href="{url}"><h3>RTX 4070 12GB</h3></a><del>3 000 zł</del><p class="price">1 200,50 zł</p></article>'
    rows = parse_page(html, platform, search_url(platform, "RTX 4070"))
    assert len(rows) == 1
    assert rows[0].price_minor == 120050
    assert rows[0].title == "RTX 4070 12GB"


@pytest.mark.parametrize("platform", PLATFORMS)
def test_jsonld_is_parsed_without_executing_javascript(platform):
    node = {
        "@type": "Product",
        "name": "iPhone 14 128GB",
        "url": demo_url(platform, "12345"),
        "offers": {"price": "1500.99", "priceCurrency": "PLN"},
        "itemCondition": "https://schema.org/UsedCondition",
    }
    page = '<script type="application/ld+json">' + json.dumps(node) + "</script>"
    rows = parse_page(page, platform, search_url(platform, "iPhone 14"))
    assert rows[0].price_minor == 150099
    assert rows[0].condition == "USED"


@pytest.mark.parametrize(
    "html,code",
    [
        ("<p>Verify you are human</p>", "ACCESS_BLOCKED"),
        ('<form action="/login"></form>', "LOGIN_REQUIRED"),
        ("<p>Inny układ strony</p>", "PARSER_CHANGED"),
    ],
)
def test_access_failure_is_never_empty_success(html, code):
    with pytest.raises(SourceError) as error:
        parse_page(html, "OLX", search_url("OLX", "x"))
    assert error.value.code == code
    assert parse_page("<p>Brak wyników</p>", "OLX", search_url("OLX", "x")) == []


def test_euro_price_is_never_silently_treated_as_pln():
    html = '<article data-cy="l-card"><a href="https://www.olx.pl/d/oferta/gpu-ID1.html"><h3>RTX 4070 12GB</h3></a><p class="price">350 €</p></article>'
    assert parse_page(html, "OLX", search_url("OLX", "x"))[0].currency == "EUR"


def test_feed_validation_and_explicit_network_flag(tmp_path):
    registry = SourceRegistry(
        [SourceConfig("OLX", mode="json", feed_path="feed.json")], tmp_path
    )
    (tmp_path / "feed.json").write_text(json.dumps([{"title": "bad"}]))
    with pytest.raises(SourceError, match="Plik danych"):
        registry.discover("OLX", search())
    registry.close()
    registry = SourceRegistry([SourceConfig("OLX")], tmp_path)
    with pytest.raises(SourceError) as error:
        registry.discover("OLX", search())
    assert error.value.code == "NETWORK_DISABLED"
    registry.close()


class Response:
    def __init__(self, code, text="", headers=None):
        self.status_code, self.text, self.headers, self.encoding = (
            code,
            text,
            headers or {},
            "utf-8",
        )

    def iter_content(self, _):
        yield self.text.encode()

    def close(self):
        pass


class Session:
    headers = {}

    def __init__(self, responses):
        self.responses, self.calls = iter(responses), []

    def get(self, url, **kwargs):
        self.calls.append(url)
        return next(self.responses)

    def close(self):
        pass


def test_robots_denial_does_not_fetch_listings():
    session = Session([Response(200, "User-agent: *\nDisallow: /")])
    transport = HttpTransport(session, sleeper=lambda _: None)
    with pytest.raises(SourceError) as error:
        transport.html(search_url("OLX", "gpu"), SourceConfig("OLX"))
    assert error.value.code == "ROBOTS_DENIED"
    assert len(session.calls) == 1


def test_rate_limit_and_unsafe_redirect():
    for response, expected in [
        (Response(429, headers={"Retry-After": "900"}), "RATE_LIMITED"),
        (Response(302, headers={"Location": "http://127.0.0.1/x"}), "UNSAFE_REDIRECT"),
    ]:
        transport = HttpTransport(Session([response]), sleeper=lambda _: None)
        with pytest.raises(SourceError) as error:
            transport._get(search_url("OLX", "x"), "OLX", 3)
        assert error.value.code == expected
