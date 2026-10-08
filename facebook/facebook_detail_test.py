from playwright.sync_api import sync_playwright


URL = "https://www.facebook.com/marketplace/item/4077987045827636/"


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            locale="pl-PL",
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        print("[1] Otwieram ofertę:")
        print(URL)

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=60000,
        )

        page.wait_for_timeout(5000)

        print("\n[2] TYTUŁ STRONY:")
        print(page.title())

        print("\n[3] ADRES:")
        print(page.url)

        print("\n[4] TREŚĆ OFERTY:")
        print("=" * 80)

        body = page.locator("body").inner_text(
            timeout=10000
        )

        print(body[:5000])

        print("=" * 80)

        browser.close()


if __name__ == "__main__":
    main()
