# monitor.py
# Полностью готовый шаблон мониторинга ИТМО для нескольких программ.
# Замените PROGRAMS своими программами и ID.

import os, json, re
from datetime import datetime
import requests

PROGRAMS = [
    {
        "name": "Фотончики",
        "url": "https://abit.itmo.ru/rating/master/budget/2397",
        "tracked_ids": ["2129111"],
    },
    {
        "name": "Наночастички",
        "url": "https://abit.itmo.ru/rating/master/budget/2396",
        "tracked_ids": ["2131095"],
    },
]

DATA_FILE = "itmo_data.json"
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=20,
    )

def load():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE,"r",encoding="utf8") as f:
            return json.load(f)
    except:
        return {}

def save(data):
    with open(DATA_FILE,"w",encoding="utf8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)

def download(url):
    r=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=20)
    r.raise_for_status()
    return r.text

def parse(html):
    m=re.search(r'<script id="__NEXT_DATA__".*?>(.*?)</script>',html,re.S)
    if not m:
        raise RuntimeError("JSON not found")
    data=json.loads(m.group(1))
    arr=data.get("props",{}).get("pageProps",{}).get("programList",{}).get("general_competition",[])
    out=[]
    for x in arr:
        out.append({
            "number":str(x.get("sspvo_id","")),
            "position":x.get("position"),
            "priority":x.get("priority"),
            "total_scores":x.get("total_scores"),
            "ia_scores":x.get("ia_scores"),
            "consent":x.get("is_send_agreement"),
        })
    return out

def summary(data,tracked,name):
    lines=[f"📊 {name}",f"Всего: {len(data)}",""]
    for a in data:
        if a["number"] not in tracked:
            continue
        lines.extend([
            f"№ {a['number']}",
            f"Позиция: {a['position']}",
            f"Приоритет: {a['priority']}",
            f"ИД: {a['ia_scores']}",
            f"Балл: {a['total_scores']}",
            f"Согласие: {'✅' if a['consent'] else '❌'}",
            ""
        ])
    return "\n".join(lines)

def compare(old,new,tracked):
    msgs=[]
    om={x["number"]:x for x in old}
    nm={x["number"]:x for x in new}
    if len(old)!=len(new):
        msgs.append(f"👥 Количество: {len(old)} → {len(new)}")
    for num in tracked:
        if num not in om or num not in nm:
            continue
        a,b=om[num],nm[num]
        if a["position"]!=b["position"]:
            msgs.append(f"{num}: позиция {a['position']} → {b['position']}")
        if a["total_scores"]!=b["total_scores"]:
            msgs.append(f"{num}: балл {a['total_scores']} → {b['total_scores']}")
        if a["priority"]!=b["priority"]:
            msgs.append(f"{num}: приоритет {a['priority']} → {b['priority']}")
        if a["consent"]!=b["consent"]:
            msgs.append(f"{num}: согласие {'появилось' if b['consent'] else 'исчезло'}")
    return msgs

def main():
    now=datetime.now().strftime("%H:%M:%S")
    previous=load()
    current_all={}
    report=[f"✅ ИТМО монитор работает",f"⏰ {now}",""]

    for p in PROGRAMS:
        try:
            current=parse(download(p["url"]))
            current_all[p["name"]]=current

            tracked = [x for x in current if x["number"] in p["tracked_ids"]]

            if tracked:
                a = tracked[0]
                report.append(
                    f"🟢 {p['name']}: {len(current)} абитуриентов\n"
                    f"🏆 Место: {a['position']}\n"
                    f"📊 Балл: {a['total_scores']}\n"
                    f"📝 Приоритет: {a['priority']}"
                )
            else:
                report.append(
                    f"🟡 {p['name']}: {len(current)} абитуриентов\n"
                    f"⚠️ Ваш ID не найден"
                )

            old=previous.get(p["name"],[])
            if not old:
                send("🚀 Первый запуск\n\n"+summary(current,p["tracked_ids"],p["name"]))
            else:
                changes=compare(old,current,p["tracked_ids"])
                if changes:
                    send("🔔 "+p["name"]+"\n\n"+"\n".join(changes)+"\n\n"+summary(current,p["tracked_ids"],p["name"]))

        except Exception as e:
            report.append(f"🔴 {p['name']}: ошибка")
            send(f"❌ Ошибка в программе {p['name']}\n{e}")

    save(current_all)
    send("\n".join(report))

if __name__=="__main__":
    main()
