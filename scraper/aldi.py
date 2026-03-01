"""
ALDI 爬虫 — cloudscraper 版，三重选择器策略
ALDI 全国统一价，Carnegie Central 和 Glen Huntly 两家价格相同。
"""
import re
import cloudscraper
from bs4 import BeautifulSoup

_scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "darwin", "mobile": False}
)

HEADERS = {
    "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Referer":         "https://www.aldi.com.au/",
}

CATEGORY_URLS = {
    "milk":    "https://www.aldi.com.au/en/groceries/dairy-eggs-chilled/milk/",
    "eggs":    "https://www.aldi.com.au/en/groceries/dairy-eggs-chilled/eggs/",
    "bread":   "https://www.aldi.com.au/en/groceries/bakery/bread/",
    "butter":  "https://www.aldi.com.au/en/groceries/dairy-eggs-chilled/butter-spreads/",
    "chicken": "https://www.aldi.com.au/en/groceries/meat-seafood/",
}

BRANCH = "Carnegie Central / Glen Huntly (统一价)"


def get_price(keyword: str) -> dict | None:
    kw_lower     = keyword.lower()
    category_url = next((u for k, u in CATEGORY_URLS.items() if k in kw_lower), None)

    if not category_url:
        print(f"    [ALDI] 未配置分类 URL: '{keyword}'")
        return None

    try:
        resp = _scraper.get(category_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [ALDI] 请求失败: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 三重策略，任意命中就返回
    return (
        _strategy_new(soup, kw_lower, keyword)
        or _strategy_old(soup, kw_lower, keyword)
        or _strategy_generic(soup, kw_lower, keyword)
    )


def _strategy_new(soup, kw_lower, keyword):
    """新版 ALDI tile 结构（2024 年后）"""
    cards = soup.select(
        "li.ft-product-tile, li[class*='product-tile'], "
        "div[class*='product-tile'], article[class*='tile']"
    )
    return _match(cards, kw_lower, keyword, "new")


def _strategy_old(soup, kw_lower, keyword):
    """旧版 ALDI 结构"""
    cards = soup.select(
        "div.tile--product, div.product-item, "
        "div[data-module='product'], li[class*='item']"
    )
    return _match(cards, kw_lower, keyword, "old")


def _strategy_generic(soup, kw_lower, keyword):
    """
    通用兜底：找包含关键词的任意块级元素里的 $x.xx 价格。
    不依赖 class 名，对 HTML 结构变化最具鲁棒性。
    """
    kw_words = kw_lower.split()
    for tag in soup.find_all(string=re.compile(kw_lower, re.I)):
        container = tag.find_parent(["li", "article", "div", "section"])
        if not container:
            continue
        text = container.get_text(" ", strip=True)
        if len(text) > 600 or not any(w in text.lower() for w in kw_words):
            continue
        price_m = re.search(r"\$\s*(\d+\.\d{2})", text)
        if price_m:
            name_el = container.select_one("h2, h3, [class*='name'], [class*='title']")
            return _build(
                name_el.get_text(strip=True) if name_el else keyword,
                float(price_m.group(1)),
                "generic",
            )
    return None


def _match(cards, kw_lower, keyword, strategy):
    kw_words = kw_lower.split()
    for card in cards:
        text = card.get_text(" ", strip=True)
        if not any(w in text.lower() for w in kw_words):
            continue
        price_m = re.search(r"\$\s*(\d+\.\d{2})", text)
        if not price_m:
            continue
        name_el = card.select_one("[class*='name'], [class*='title'], h2, h3")
        name    = name_el.get_text(strip=True) if name_el else keyword
        return _build(name, float(price_m.group(1)), strategy)
    return None


def _build(name, price, source):
    return {
        "store":      "ALDI",
        "branch":     BRANCH,
        "name":       name,
        "price":      price,
        "was_price":  None,
        "on_special": False,
        "source":     source,
    }
