import requests
import json
import os
from bs4 import BeautifulSoup
from telegram import Bot
from datetime import datetime

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

DATA_FILE = "data.json"


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def get_woolworths():
    url = "https://www.woolworths.com.au/shop/browse/specials"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    deals = {}

    for item in soup.select(".product-tile")[:20]:
        name = item.select_one(".product-title")
        price = item.select_one(".price-dollars")

        if name and price:
            deals[name.text.strip()] = price.text.strip()

    return deals


def check_price_changes(new_data, old_data):
    changed = []

    for product, price in new_data.items():
        if product not in old_data:
            changed.append(f"🆕 {product} - ${price}")
        elif old_data[product] != price:
            changed.append(f"⬇️ {product} - ${price} (原价 ${old_data[product]})")

    return changed


def main():
    old_data = load_data()
    new_data = get_woolworths()

    print("DEBUG NEW DATA:", new_data)

    # 强制发送一条测试消息（非常重要）
    bot.send_message(
        chat_id=CHAT_ID,
        text="✅ Supermarket bot 测试消息：Workflow 正常运行"
    )

    changes = check_price_changes(new_data, old_data)

    if changes:
        message = "🛒 Carnegie 今日新特价\n\n"
        message += "\n".join(changes)

        bot.send_message(chat_id=CHAT_ID, text=message)

    save_data(new_data)

if __name__ == "__main__":
    main()
