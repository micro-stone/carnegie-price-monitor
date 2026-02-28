import requests
import re

# Carnegie 门店信息（已硬编码）
CARNEGIE_STORES = [
    {"id": "3298", "name": "Carnegie North (Koornang Rd)"},
    # 第二家 Kokaribb Rd 门店 ID 需要通过 find_store_id() 确认
    # 通常两家门店价格相同，监控 3298 即可
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.woolworths.com.au/",
    # 设置 Carnegie North 为当前门店，使 Specials 显示正确门店价格
    "Cookie": "wow-store-id=3298; wow-postcode=3163",
}


def get_price(product_id: str) -> dict | None:
    """
    通过商品 ID 查询 Woolworths Carnegie 价格。
    优先使用 detail API，失败则降级到 HTML 提取。
    """
    result = _api_price(product_id)
    if result:
        return result
    print(f"  [WW] API 失败，尝试 HTML 提取...")
    return _html_price(product_id)


def _api_price(product_id: str) -> dict | None:
    url = f"https://www.woolworths.com.au/apis/ui/product/detail/{product_id}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # API 返回结构可能是 {"Product": {...}} 或直接是商品对象
            p = data.get("Product") or (data[0] if isinstance(data, list) else data)
            price = p.get("Price")
            if price:
                return {
                    "store": "Woolworths",
                    "branch": "Carnegie North (3298)",
                    "name": p.get("Name", ""),
                    "price": float(price),
                    "was_price": p.get("WasPrice"),
                    "unit_price": p.get("CupString", ""),
                    "on_special": bool(p.get("IsOnSpecial")),
                }
    except Exception as e:
        print(f"  [WW] detail API 异常: {e}")
    return None


def _html_price(product_id: str) -> dict | None:
    """备用：从 HTML 页面提取嵌入的 JSON"""
    url = f"https://www.woolworths.com.au/shop/productdetails/{product_id}"
    try:
        resp = requests.get(
            url,
            headers={**HEADERS, "Accept": "text/html"},
            timeout=20,
        )
        html = resp.text.replace("&q;", '"').replace("&amp;", "&")
        price_m = re.search(r'"Price":([\d.]+)', html)
        was_m = re.search(r'"WasPrice":([\d.]+)', html)
        name_m = re.search(r'"Name":"([^"]+)"', html)
        if price_m:
            return {
                "store": "Woolworths",
                "branch": "Carnegie North (3298)",
                "name": name_m.group(1) if name_m else f"ID:{product_id}",
                "price": float(price_m.group(1)),
                "was_price": float(was_m.group(1)) if was_m else None,
                "on_special": was_m is not None,
                "source": "html",
            }
    except Exception as e:
        print(f"  [WW] HTML 提取异常: {e}")
    return None
