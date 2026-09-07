"""
Daily print-edition metadata collector.

Policy:
- Collect only publicly available page/article metadata.
- Do not bypass login/paywalls.
- Do not republish full article bodies.
- Respect each publisher's terms/robots.txt before production use.

This starter implements a conservative MK collector and leaves adapters explicit.
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")
OUT = Path(__file__).parent / "data" / "latest.json"

PAPERS = [
    {"id":"mk","name":"매일경제","source":"https://www.mk.co.kr/today-paper/","status":"자동 수집 가능"},
    {"id":"donga","name":"동아일보","source":"https://www.donga.com/news","status":"자동 수집 가능"},
    {"id":"hani","name":"한겨레","source":"https://newsviews.hani.co.kr/","status":"로그인/구독 기반"},
    {"id":"khan","name":"경향신문","source":"https://epaper.khan.co.kr/","status":"유료 지면보기"},
    {"id":"hankyung","name":"한국경제","source":"https://www.hankyung.com/","status":"지면 메타데이터 연동 대상"},
    {"id":"chosun","name":"조선일보","source":"https://www.chosun.com/","status":"어댑터 추가 필요"},
    {"id":"joongang","name":"중앙일보","source":"https://www.joongang.co.kr/","status":"어댑터 추가 필요"},
    {"id":"seoul","name":"서울신문","source":"https://www.seoul.co.kr/","status":"지면 메타데이터 연동 대상"},
]

HEADERS = {"User-Agent":"Mozilla/5.0 (compatible; PersonalPrintReader/1.0)"}

def text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()

def collect_mk(date: str) -> dict:
    url = f"https://www.mk.co.kr/today-paper/?date={date.replace('-','')}&section=A"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Publisher markup can change. This intentionally uses heading-based discovery,
    # then captures nearby links/text without copying article bodies.
    pages = []
    for h in soup.find_all(["h2","h3","strong"]):
        m = re.fullmatch(r"(\d+)면", text(h))
        if not m:
            continue
        num = int(m.group(1))
        container = h.parent
        titles = []
        for a in container.find_all("a", href=True):
            t = text(a)
            if len(t) >= 8 and t not in titles:
                href = a["href"]
                if href.startswith("/"):
                    href = "https://www.mk.co.kr" + href
                titles.append((t, href))
        if titles:
            pages.append({
                "number": num,
                "section": "",
                "articles": [{"title":t, "summary":"", "url":u} for t,u in titles[:12]]
            })

    return {"id":"mk","name":"매일경제","date":date,"status":"자동 수집 가능","source":url,"pages":pages}

def empty_paper(meta: dict, date: str) -> dict:
    return {**meta, "date": date, "pages": []}

def main():
    today = datetime.now(KST).date().isoformat()
    papers = []
    for p in PAPERS:
        if p["id"] == "mk":
            try:
                papers.append(collect_mk(today))
            except Exception as e:
                item = empty_paper(p, today)
                item["status"] = f"수집 실패: {type(e).__name__}"
                papers.append(item)
        else:
            papers.append(empty_paper(p, today))

    payload = {"generated_at": datetime.now(KST).isoformat(), "papers": papers}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {OUT}")

if __name__ == "__main__":
    main()
