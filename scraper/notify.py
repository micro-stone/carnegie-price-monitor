import os
import requests


def send(text: str) -> bool:
    token   = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":                  chat_id,
                "text":                     text,
                "parse_mode":               "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"  [Telegram] 发送失败: {e}")
        return False


def price_change_message(alerts: list) -> str:
    drops = sorted([a for a in alerts if a["change"] < 0], key=lambda x: x["change"])
    rises = sorted([a for a in alerts if a["change"] > 0], key=lambda x: -x["change"])
    lines = ["🛒 *Carnegie 3163 价格变动*\n"]

    if drops:
        lines.append("📉 *降价*")
        for a in drops:
            pct = abs(a["change"] / a["old_price"] * 100)
            tag = " 🏷️特价" if a.get("on_special") else ""
            lines.append(
                f"• *{a['item']}* — {a['store']} {a['branch']}\n"
                f"  ~~${a['old_price']:.2f}~~ → *${a['new_price']:.2f}*"
                f"  (-${abs(a['change']):.2f} / -{pct:.0f}%{tag})"
            )
        lines.append("")

    if rises:
        lines.append("📈 *涨价*")
        for a in rises:
            pct = a["change"] / a["old_price"] * 100
            lines.append(
                f"• *{a['item']}* — {a['store']} {a['branch']}\n"
                f"  ~~${a['old_price']:.2f}~~ → *${a['new_price']:.2f}*"
                f"  (+${a['change']:.2f} / +{pct:.0f}%)"
            )
    return "\n".join(lines)


def daily_summary_message(prices: dict) -> str:
    lines = [
        "📊 *Carnegie 3163 每日价格*",
        "📍 Woolworths #3298 | Coles Carnegie | ALDI\n",
    ]
    for item_name, stores in prices.items():
        valid = {k: v for k, v in stores.items() if v and v.get("price")}
        if not valid:
            lines.append(f"• *{item_name}* — 暂无数据")
            continue
        best_store = min(valid, key=lambda k: valid[k]["price"])
        best_price = valid[best_store]["price"]
        parts = [
            f"{s}: ${d['price']:.2f}{'🏷️' if d.get('on_special') else ''}"
            for s, d in valid.items()
        ]
        lines.append(f"*{item_name}*  最优 *${best_price:.2f}* ({best_store})")
        lines.append(f"  {' | '.join(parts)}")
    return "\n".join(lines)
