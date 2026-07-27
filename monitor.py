import os
import json
import re
from datetime import datetime

import requests

PROGRAMS = [
    {
        "name": "Фотончики",
        "url": "https://abit.itmo.ru/rating/master/budget/2397",
        "tracked_ids": [
            "2129111"
            
        ]
    },

    {
        "name": "Наночастички",
        "url": "https://abit.itmo.ru/rating/master/budget/2396",
        "tracked_ids": [
            "2131095"
          
        ]
    }
]

all_current[program["name"]] = current

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]



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
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}


def save_current(data):
    with open(DATA_FILE, "w", encoding="utf8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def download(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(
        url,
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


def summary(data, tracked_ids, program_name):
    tracked = []

    for app in data:
        if app["number"] in tracked_ids:
            tracked.append(app)

    p1 = sum(
        1
        for x in data
        if x["priority"] == 1
    )

    text = []

    text.append(f"📊 ИТМО — {program_name}")
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


def compare(old, new, tracked_ids):

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

    for num in tracked_ids:

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

    all_current = {}
    previous = load_previous()

    for program in PROGRAMS:

        html = download(program["url"])
        current = parse(html)

        all_current[program["name"]] = current

        send_telegram(
            f"✅ {program['name']} работает\n"
            f"⏰ Проверка: {now}\n"
            f"👥 Абитуриентов: {len(current)}"
        )

        old_data = previous.get(program["name"], [])

        if not old_data:

            send_telegram(
                f"🚀 Первый запуск — {program['name']}\n\n"
                + summary(
                    current,
                    program["tracked_ids"],
                    program["name"]
                )
            )

        else:

            changes = compare(
                old_data,
                current,
                program["tracked_ids"]
            )

            if changes:

                send_telegram(
                    f"🔔 ОБНАРУЖЕНЫ ИЗМЕНЕНИЯ — {program['name']}!\n\n"
                    + "\n\n".join(changes)
                    + "\n\n"
                    + summary(
                        current,
                        program["tracked_ids"],
                        program["name"]
                    )
                )

            else:
                print(f"{program['name']}: изменений нет")

    save_current(all_current)

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
