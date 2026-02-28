import json
from playwright.sync_api import sync_playwright

def get_woolworths_deals():
    url = "https://www.woolworths.com.au/shop/browse/specials"

    deals = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=60000)
        page.wait_for_timeout(8000)

        products = page.query_selector_all(".product-tile")

        for item in products[:30]:
            name = item.query_selector(".product-title")
            price = item.query_selector(".price-dollars")

            if name and price:
                deals[name.inner_text().strip()] = price.inner_text().strip()

        browser.close()

    return deals
