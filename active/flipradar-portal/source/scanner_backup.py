from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from database import init_db, offer_exists, save_offer
import re

SEARCH_URL = (
    "https://www.olx.pl/elektronika/komputery/komputery-stacjonarne/"
    "?search%5Border%5D=created_at:desc"
)


def get_offer_id(url):
    match = re.search(r"(ID[a-zA-Z0-9]+)", url)

    if match:
        return match.group(1)

    return None


def parse_price(text):
    # Obsługuje np.:
    # 1 500 zł
    # 1500 zł
    # 1 500,00 zł

    match = re.search(
        r"(\d[\d\s]*(?:[,.]\d{2})?)\s*zł",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = match.group(1)
    value = value.replace(" ", "")
    value = value.replace(",", ".")

    try:
        return int(float(value))
    except ValueError:
        return None


def clean_url(url):
    # Usuwamy tracking OLX
    return url.split("?")[0]


init_db()

with sync_playwright() as p:

    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={"width": 1400, "height": 900},
        locale="pl-PL"
    )

    print("Skanuję OLX...")

    page.goto(
        SEARCH_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(4000)

    cards = page.locator('[data-cy="l-card"]')

    count = cards.count()

    print(f"Znaleziono {count} ofert.")

    new_count = 0

    for i in range(count):

        card = cards.nth(i)

        try:

            text = card.inner_text().strip()

            links = card.locator("a")

            if links.count() == 0:
                continue

            href = links.first.get_attribute("href")

            if not href:
                continue

            url = urljoin(
                "https://www.olx.pl",
                href
            )

            url = clean_url(url)

            offer_id = get_offer_id(url)

            if not offer_id:
                continue

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            if not lines:
                continue

            title = lines[0]

            price = parse_price(text)

            # Oferta już była widziana
            if offer_exists(offer_id):
                continue

            save_offer(
                offer_id,
                title,
                price,
                url
            )

            new_count += 1

            print("\n" + "=" * 80)
            print("NOWA OFERTA")
            print(f"ID:    {offer_id}")
            print(f"TYTUŁ: {title}")

            if price:
                print(f"CENA:  {price} zł")
            else:
                print("CENA:  nie rozpoznano")

            print(f"LINK:  {url}")

        except Exception as e:
            print(f"Błąd: {e}")

    print("\n" + "=" * 80)
    print(f"Nowych ofert: {new_count}")

    browser.close()
