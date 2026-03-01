"""
Coles 爬虫 — cloudscraper 版

Coles 的商品搜索 API BASE_URL 会轮换，无法永久硬编码。
解决策略：
  1. 读缓存的有效 URL（data/coles_api_url.txt）
  2. 缓存失效时，从搜索页 HTML 里动态解析当前 API URL
  3. 最后兜底：直接用 www.coles.com.au 主域
"""
import re
import json
from pathlib import Path
import cloudscraper
from bs4 import BeautifulSoup

STORE_ID   = "7724"   # Coles Carnegie Central
CACHE_FILE = Path("data/coles_api_url.txt")
_API_PATH  = "/api/2.0/market/products"

_scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "darwin", "mobile": False}
)

BASE_HEADERS = {
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-AU,en;q=0.9",
    "Origin":          "https://www.coles.com.au",
    "Referer":         "https://www.coles.com.au/",
}


def get_price(query: str) -> dict | None:
    base_url = _get_base_url()
    if not base_url:
        return None

    result = _fetch(base_url, query, store_id=STORE_ID)
    if result:
        return result

    # storeId 可能无效，不带 storeId 再试一次
    result = _fetch(base_url, query, store_id=None)
    if result:
        return result

    # URL 可能已轮换，强制刷新再试
    print(f"    [Coles] URL 可能失效，重新发现...")
    CACHE_FILE.unlink(missing_ok=True)
    base_url = _get_base_url(force=True)
    if base_url:
        return _fetch(base_url, query, store_id=None)

    return None


def _fetch(base_url: str, query: str, store_id: str | None) -> dict | None:
    url    = base_url.rstrip("/") + _API_PATH
    params = {"q": query, "page": 1, "pageSize": 5}
    if store_id:
        params["storeId"] = store_id
    try:
        resp = _scraper.get(url, headers=BASE_HEADERS, params=params, timeout=20)
        if resp.status_code not in (200, 201):
            return None
        data    = resp.json()
        results = data.get("results", [])
        if not results:
            return None
        item    = results[0]
        pricing = item.get("pricing", {})
        price   = pricing.get("now") or item.get("price")
        if not price:
            return None
        return {
            "store":      "Coles",
            "branch":     "Carnegie Central",
            "name":       item.get("name", query),
            "price":      float(price),
            "was_price":  pricing.get("was"),
            "unit":       pricing.get("unit", {}).get("ofMeasurePrice", ""),
            "on_special": pricing.get("promotionType") is not None,
            "source":     "api",
        }
    except Exception as e:
        print(f"    [Coles] 请求异常: {e}")
        return None


def _get_base_url(force: bool = False) -> str | None:
    if not force and CACHE_FILE.exists():
        cached = CACHE_FILE.read_text().strip()
        if cached:
            return cached
    url = _discover()
    if url:
        CACHE_FILE.parent.mkdir(exist_ok=True)
        CACHE_FILE.write_text(url)
    return url


def _discover() -> str | None:
    """从 Coles 搜索页的 __NEXT_DATA__ 或 JS 中提取 API BASE_URL"""
    try:
        resp = _scraper.get(
            "https://www.coles.com.au/search?q=milk",
            headers={**BASE_HEADERS, "Accept": "text/html"},
            timeout=25,
        )
        html = resp.text

        # 方法1: __NEXT_DATA__ runtimeConfig
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data    = json.loads(m.group(1))
                runtime = (data.get("runtimeConfig")
                           or data.get("publicRuntimeConfig", {}))
                for key in ("API_HOST", "API_BASE", "NEXT_PUBLIC_API_BASE", "apiBase"):
                    val = runtime.get(key, "")
                    if val and "coles.com.au" in val:
                        print(f"    [Coles] 从 __NEXT_DATA__ 找到 API URL: {val}")
                        return val.rstrip("/")
            except Exception:
                pass

        # 方法2: JS 里正则找 API 子域
        for pat in [
            r'["\'](https://[a-z0-9\-]+\.coles\.com\.au)["\']',
            r'baseURL\s*[:=]\s*["\'](https://[^"\']+)["\']',
        ]:
            for found in re.findall(pat, html):
                if "www.coles.com.au" not in found:
                    print(f"    [Coles] 从 JS 找到 API URL: {found}")
                    return found.rstrip("/")

        # 方法3: 兜底用主站
        print("    [Coles] 使用主站 URL 作为兜底")
        return "https://www.coles.com.au"

    except Exception as e:
        print(f"    [Coles] URL 发现失败: {e}")
        return None
