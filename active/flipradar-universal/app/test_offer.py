from playwright.sync_api import sync_playwright
from offer_parser import extract_offer, print_offer

URL = "https://www.olx.pl/d/oferta/komputer-ryzen-rtx-CID99-ID1ct2Ku.html"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page(
        viewport={"width": 1400, "height": 1000},
        locale="pl-PL"
    )

    data = extract_offer(page, URL)

    if data:
        print_offer(data)

    browser.close()
