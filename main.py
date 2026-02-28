import os
import json
from datetime import datetime
from telegram import Bot

from crawler.woolworths import get_woolworths_deals

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

bot = Bot(token=BOT_TOKEN)

DATA_FILE = "storage/data.json"


def load_db():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_db(data):
    os.makedirs("storage", exist_ok=True)

    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def detect_price_drop(new_data, old_data, threshold=0.2):
    alerts = []

    for product, price in new_data.items():

        try:
            price_float = float(price.replace("$", ""))

            if product in old_data:
                old_price = float(old_data[product].replace("$", ""))

                if old_price > price_float * (1 + threshold):
                    alerts.append(
                        f"⬇️ 降价 {product}\n"
                        f"原价 ${old_price}\n"
                        f"现价 ${price_float}"
                    )

            else:
                alerts.append(f"🆕 新商品 {product} - ${price_float}")

        except:
            continue

    return alerts


def main():
    print("开始终极稳定版抓取")

    old_db = load_db()
    new_db = get_woolworths_deals()

    alerts = detect_price_drop(new_db, old_db)

    if alerts:
        message = "🛒 Carnegie 超市特价监控\n\n"
        message += "\n\n".join(alerts)
        message += f"\n\n更新时间 {datetime.now()}"

        bot.send_message(chat_id=CHAT_ID, text=message)

    save_db(new_db)


if __name__ == "__main__":
    main()
