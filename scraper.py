from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

KST = ZoneInfo("Asia/Seoul")
OUT = Path(__file__).parent / "data" / "latest.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PersonalPrintReader/1.1)"}

PAPERS = [
    {"id":"mk","name":"매일경제","source":"https://www.mk.co.kr/today-paper/","status":"수집기 개선 예정"},
    {"id":"donga","name":"동아일보","source":"https://www.donga.com/news/Pdf","status":"자동 수집 가능"},
    {"id":"hani","name":"한겨레","source":"https://newsviews.hani.co.kr/","status":"로그인/구독 기반"},
    {"id":"khan","name":"경향신문","source":"https://epaper.khan.co.kr/","status":"유료 지면보기"},
    {"id":"hankyung","name":"한국경제","source":"https://www.hankyung.com/","status":"연동 예정"},
    {"id":"chosun","name":"조선일보","source":"https://www.chosun.com/","status":"연동 예정"},
    {"id":"joongang","name":"중앙일보","source":"https://www.joongang.co.kr/","status":"연동 예정"},
    {"id":"seoul","name":"서울신문","source":"https://www.seoul.co.kr/","status":"연동 예정"},
]

def empty(meta, date):
    return {**meta, "date": date, "pages": []}

def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()

def collect_donga(date: str) -> dict:
    """
    동아일보가 공개한 지면 목차의 면/섹션/기사 제목을 수집한다.
    PDF 파일이나 기사 본문은 다운로드하지 않는다.
    """
    ymd = date.replace("-", "")
    url = f"https://www.donga.com/news/Pdf?ymd={ymd}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    pages = []
    seen = set()

    # 페이지 텍스트에서 A1/B2/C3 같은 지면 헤더를 찾는다.
    # 실제 사이트 마크업 변경에 대비해 li/div 계열을 폭넓게 검사한다.
    page_re = re.compile(r"^([A-Z])\s*(\d+)\s*(.*)$")

    for node in soup.find_all(["li", "div", "section", "article"]):
        direct = clean(node.get_text(" ", strip=True))
        if not direct or len(direct) > 2500:
            continue

        # 첫 텍스트 조각에서 지면 번호 탐색
        first = None
        if node.contents:
            for child in node.contents:
                if isinstance(child, str):
                    t = clean(child)
                else:
                    t = clean(getattr(child, "get_text", lambda *a, **k: "")(" ", strip=True))
                if t:
                    first = t
                    break
        first = first or direct

        m = page_re.match(first)
        if not m:
            # "A1 종합 ..."처럼 전체 문자열에 붙어 있는 경우
            m = page_re.match(direct)
        if not m:
            continue

        sec, num, rest = m.group(1), int(m.group(2)), clean(m.group(3))
        key = f"{sec}{num}"
        if key in seen:
            continue

        # 링크가 있는 기사 제목 우선
        articles = []
        title_seen = set()
        for a in node.find_all("a", href=True):
            title = clean(a.get_text(" ", strip=True))
            if not title or len(title) < 4 or title in title_seen:
                continue
            href = urljoin("https://www.donga.com", a.get("href"))
            # 네비게이션성 링크 제외
            if title in {"동아일보", "PDF", "1일치 결제하기"}:
                continue
            title_seen.add(title)
            articles.append({"title": title, "summary": "", "url": href})

        # 링크가 없는 목차도 텍스트 항목으로 보존
        if not articles:
            for li in node.find_all("li", recursive=False):
                title = clean(li.get_text(" ", strip=True))
                if title and not page_re.match(title) and title not in title_seen:
                    title_seen.add(title)
                    articles.append({"title": title, "summary": "", "url": "https://www.donga.com/news"})

        # 전면광고 감지
        is_ad = "전면광고" in direct
        section_name = "전면광고" if is_ad else (rest.split(" ")[0] if rest else "")

        if articles or is_ad:
            seen.add(key)
            pages.append({
                "number": num,
                "label": key,
                "edition_section": sec,
                "section": section_name,
                "is_ad": is_ad,
                "articles": articles[:20]
            })

    pages.sort(key=lambda p: (p["edition_section"], p["number"]))

    # HTML 구조가 바뀌어 파싱에 실패했음을 조용히 숨기지 않는다.
    status = "자동 수집 가능" if pages else "수집 실패: 지면 구조 확인 필요"
    return {
        "id": "donga",
        "name": "동아일보",
        "date": date,
        "status": status,
        "source": url,
        "pages": pages
    }

def main():
    today = datetime.now(KST).date().isoformat()
    papers = []
    for meta in PAPERS:
        try:
            if meta["id"] == "donga":
                papers.append(collect_donga(today))
            else:
                papers.append(empty(meta, today))
        except Exception as e:
            item = empty(meta, today)
            item["status"] = f"수집 실패: {type(e).__name__}"
            papers.append(item)

    payload = {"generated_at": datetime.now(KST).isoformat(), "papers": papers}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"updated {OUT}")
    for p in papers:
        print(p["name"], p["status"], len(p["pages"]))

if __name__ == "__main__":
    main()
