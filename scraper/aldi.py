"""
ALDI 爬虫 — 更新版选择器 + 多策略提取
ALDI 全国统一价，不需要 store ID。
"""
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

CATEGORY_URLS = {
    "milk":    "https://www.aldi.com.au/en/groceries/dairy-eggs-chilled/milk/",
    "eggs":    "https://www.aldi.com.au/en/groceries/dairy-eggs-chilled/eggs/",
    "bread":   "https://www.aldi.com.au/en/groceries/bakery/bread/",
    "butter":  "https://www.aldi.com.au/en/groceries/dairy-eggs-chilled/butter-spreads/",
    "chicken": "https://www.aldi.com.au/en/groceries/meat-seafood/",
}


def get_price(keyword: str) -> dict | None:
    kw_lower = keyword.lower()
    category_url = None
    for key, url in CATEGORY_URLS.items():
        if key in kw_lower:
            category_url = url
            break

    if not category_url:
        print(f"  [ALDI] 无对应分类 URL: '{keyword}'")
        return None

    try:
        resp = requests.get(category_url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ALDI] 请求失败: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 尝试多套选择器（ALDI 网站有几种不同版本的 HTML 结构）
    # 策略1: 新版 ALDI 模板
    result = _try_selector_v1(soup, kw_lower, category_url)
    if result:
        return result

    # 策略2: 旧版 ALDI 模板
    result = _try_selector_v2(soup, kw_lower, category_url)
    if result:
        return result

    # 策略3: 全文搜索 — 在任何含关键词的 <li> 或 <article> 里找价格
    result = _try_generic(soup, kw_lower)
    if result:
        return result

    print(f"  [ALDI] 所有策略均未找到 '{keyword}'，可能需要人工更新选择器")
    return None


def _try_selector_v1(soup, kw_lower, url) -> dict | None:
    """新版 ALDI 模板（2024年后）"""
    cards = soup.select(
        "li.ft-product-tile, "
        "li[class*='product'], "
        "div[class*='product-tile'], "
        "article[class*='tile']"
    )
    return _search_cards(cards, kw_lower, "v1")


def _try_selector_v2(soup, kw_lower, url) -> dict | None:
    """旧版 ALDI 模板"""
    cards = soup.select(
        "div.tile--product, "
        "div.product-item, "
        "div[data-module='product']"
    )
    return _search_cards(cards, kw_lower, "v2")


def _try_generic(soup, kw_lower) -> dict | None:
    """通用策略：找包含关键词文字的块级元素里的价格"""
    # 找所有含关键词的文字节点的父容器
    for tag in soup.find_all(string=re.compile(kw_lower, re.I)):
        container = tag.find_parent(["li", "article", "div", "section"])
        if not container:
            continue
        text = container.get_text(" ", strip=True)
        price_m = re.search(r"\$\s*(\d+\.\d{2})", text)
        if price_m and len(text) < 500:  # 避免匹配太大的容器
            name_m = re.search(r"([A-Za-z][^$\n]{5,60})", text)
            return {
                "store": "ALDI",
                "branch": "Carnegie Central / Glen Huntly (统一价)",
                "name": name_m.group(1).strip() if name_m else keyword,
                "price": float(price_m.group(1)),
                "was_price": None,
                "on_special": False,
                "source": "generic",
            }
    return None


def _search_cards(cards, kw_lower, strategy) -> dict | None:
    kw_words = kw_lower.split()
    for card in cards:
        text = card.get_text(" ", strip=True)
        # 关键词匹配
        if not any(w in text.lower() for w in kw_words):
            continue

        # 提取价格（$2.99 格式）
        price_m = re.search(r"\$\s*(\d+\.\d{2})", text)
        if not price_m:
            continue

        # 提取商品名（第一个较短的文字块）
        name_el = (
            card.select_one("[class*='name'], [class*='title'], h2, h3")
        )
        name = name_el.get_text(strip=True) if name_el else text[:60]

        return {
            "store": "ALDI",
            "branch": "Carnegie Central / Glen Huntly (统一价)",
            "name": name,
            "price": float(price_m.group(1)),
            "was_price": None,
            "on_special": False,
            "source": f"selector_{strategy}",
        }
    return None
