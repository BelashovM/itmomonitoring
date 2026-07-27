import os
import json
import re
from datetime import datetime

import requests

URL = "https://abit.itmo.ru/rating/master/budget/2397"

DATA_FILE = "itmo_data.json"

TRACKED_IDS = [
    "2129111",
    "2131095"
]

BOT_TOKEN = '7860640743:AAGq_jSWnY6gfm6i9BrnDrUiwl9I2cJDTyA'
CHAT_ID = '947777152'



def send_telegram(text):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": text
            },
            timeout=20,
        )

        if response.status_code == 200:
            print("Telegram OK")
        else:
            print(response.text)

    except Exception as e:
        print(e)


def load_previous():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return []


def save_current(data):
    with open(DATA_FILE, "w", encoding="utf8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def download():
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        URL,
        headers=headers,
        timeout=20
    )

    r.raise_for_status()

    return r.text


def parse(html):
    match = re.search(
        r'<script id="__NEXT_DATA__".*?>(.*?)</script>',
        html,
        re.S,
    )

    if not match:
        raise Exception("JSON not found")

    data = json.loads(match.group(1))

    general = (
        data
        .get("props", {})
        .get("pageProps", {})
        .get("programList", {})
        .get("general_competition", [])
    )

    result = []

    for x in general:
        result.append(
            {
                "number": str(x.get("sspvo_id", "")),
                "position": x.get("position"),
                "priority": x.get("priority"),
                "exam_type": x.get("exam_type"),
                "ia_scores": x.get("ia_scores"),
                "exam_scores": x.get("exam_scores"),
                "total_scores": x.get("total_scores"),
                "average": x.get("diploma_average"),
                "consent": x.get("is_send_agreement"),
            }
        )

    return result


def summary(data):
    tracked = []

    for app in data:
        if app["number"] in TRACKED_IDS:
            tracked.append(app)

    p1 = sum(
        1
        for x in data
        if x["priority"] == 1
    )

    text = []

    text.append("📊 ИТМО")
    text.append("")
    text.append(f"Всего: {len(data)}")
    text.append(f"Приоритет 1: {p1}")
    text.append("")

    for app in tracked:

        medal = "📍"

        if app["position"] == 1:
            medal = "🥇"

        elif app["position"] == 2:
            medal = "🥈"

        elif app["position"] == 3:
            medal = "🥉"

        text.append(f"№ {app['number']}")
        text.append(f"{medal} Позиция: {app['position']}")
        text.append(f"Приоритет: {app['priority']}")
        text.append(f"ИД: {app['ia_scores']}")
        text.append(f"Балл: {app['total_scores']}")
        text.append(
            "Согласие: "
            + (
                "✅ Да"
                if app["consent"]
                else "❌ Нет"
            )
        )
        text.append("")

    return "\n".join(text)


def compare(old, new):

    messages = []

    old_map = {
        x["number"]: x
        for x in old
    }

    new_map = {
        x["number"]: x
        for x in new
    }

    if len(old) != len(new):
        messages.append(
            f"👥 Количество абитуриентов изменилось\n{len(old)} → {len(new)}"
        )

    for num in TRACKED_IDS:

        if num not in old_map:
            continue

        if num not in new_map:
            continue

        a = old_map[num]
        b = new_map[num]

        if a["position"] != b["position"]:
            messages.append(
                f"📈 {num}\n"
                f"Позиция {a['position']} → {b['position']}"
            )

        if a["total_scores"] != b["total_scores"]:
            messages.append(
                f"📊 {num}\n"
                f"Балл {a['total_scores']} → {b['total_scores']}"
            )

        if a["consent"] != b["consent"]:
            messages.append(
                f"📄 {num}\n"
                f"Согласие "
                f"{'появилось ✅' if b['consent'] else 'исчезло ❌'}"
            )

        if a["priority"] != b["priority"]:
            messages.append(
                f"⭐ {num}\n"
                f"Приоритет {a['priority']} → {b['priority']}"
            )

    return messages


def main():

    now = datetime.now().strftime("%H:%M:%S")

    print(now)

    html = download()

    current = parse(html)

    previous = load_previous()


    # сообщение о том, что проверка работает
    send_telegram(
        f"✅ ИТМО монитор работает\n"
        f"⏰ Проверка: {now}\n"
        f"👥 Абитуриентов: {len(current)}"
    )


    if not previous:

        send_telegram(
            "🚀 Первый запуск\n\n"
            + summary(current)
        )

    else:

        changes = compare(
            previous,
            current
        )

        if changes:

            send_telegram(
                "🔔 ОБНАРУЖЕНЫ ИЗМЕНЕНИЯ!\n\n"
                + "\n\n".join(changes)
                + "\n\n"
                + summary(current)
            )

        else:

            print("Изменений нет")


    save_current(current)

if __name__ == "__main__":

    try:
        main()

    except Exception as e:

        print(e)

        try:
            send_telegram(
                f"❌ Ошибка\n\n{e}"
            )
        except:
            pass

        raise
