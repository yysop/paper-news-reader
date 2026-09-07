from __future__ import annotations
import json, re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup, NavigableString, Tag

KST=ZoneInfo("Asia/Seoul")
ROOT=Path(__file__).parent
DATA=ROOT/"data"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; PersonalPrintReader/2.0)"}

def clean(s): return re.sub(r"\s+"," ",s or "").strip()

def fetch(url):
    r=requests.get(url,headers=HEADERS,timeout=30)
    r.raise_for_status()
    return r

def article(title,url,summary=""): return {"title":clean(title),"url":url,"summary":clean(summary)}

def collect_donga(date):
    ymd=date.replace("-","")
    url=f"https://www.donga.com/news/Pdf?ymd={ymd}"
    soup=BeautifulSoup(fetch(url).text,"html.parser")
    text=clean(soup.get_text(" ",strip=True))
    # 동아가 비발행일을 명시하는 경우
    if "신문이 발행되지 않았습니다" in text and date in text.replace("년 ","-").replace("월 ","-"):
        return {"id":"donga","name":"동아일보","date":date,"status":"비발행일","source":url,"pages":[],"message":"해당 날짜에는 신문이 발행되지 않았습니다."}

    pages=[]
    seen=set()
    # 지면 헤더(A1, A2...)를 텍스트 노드에서 찾고, 다음 지면 헤더 전까지의 링크를 기사로 수집
    candidates=[]
    for tag in soup.find_all(True):
        own=" ".join(clean(x) for x in tag.find_all(string=True, recursive=False) if clean(x))
        m=re.fullmatch(r"([A-Z])\s*(\d+)(?:\s+(.+))?",own)
        if m:
            candidates.append((tag,m.group(1),int(m.group(2)),clean(m.group(3) or "")))

    for tag,ed,num,section in candidates:
        key=f"{ed}{num}"
        if key in seen: continue
        arts=[]
        # 부모 컨테이너에서 이 헤더 다음 형제들을 훑음
        parent=tag.parent
        start=False
        for node in parent.children:
            if node is tag:
                start=True; continue
            if not start: continue
            if isinstance(node,Tag):
                nt=clean(node.get_text(" ",strip=True))
                if re.match(r"^[A-Z]\s*\d+\b",nt): break
                for a in node.find_all("a",href=True):
                    t=clean(a.get_text(" ",strip=True))
                    if len(t)>=4 and t not in [x["title"] for x in arts]:
                        arts.append(article(t,urljoin("https://www.donga.com",a["href"])))
        # 폴백: 바로 뒤 인접 요소들
        if not arts:
            node=tag
            for _ in range(12):
                node=node.find_next()
                if not node: break
                nt=clean(node.get_text(" ",strip=True))
                if node is not tag and re.fullmatch(r"[A-Z]\s*\d+(?:\s+.*)?",nt): break
                if node.name=="a" and node.get("href"):
                    t=clean(node.get_text(" ",strip=True))
                    if len(t)>=4 and t not in [x["title"] for x in arts]:
                        arts.append(article(t,urljoin("https://www.donga.com",node["href"])))
        if arts:
            seen.add(key)
            pages.append({"key":key,"label":key,"edition":ed,"number":num,"section":section or "지면","articles":arts[:20]})

    # 더 강한 폴백: 페이지 전체 텍스트에서 A1/A2를 찾고 그 사이의 li 링크를 매핑
    if not pages:
        for li in soup.find_all("li"):
            txt=clean(li.get_text(" ",strip=True))
            m=re.match(r"^([A-Z])(\d+)\s*(.*)$",txt)
            if not m: continue
            ed,num,rest=m.group(1),int(m.group(2)),clean(m.group(3))
            arts=[]
            for a in li.find_all("a",href=True):
                t=clean(a.get_text(" ",strip=True))
                if t and not re.match(r"^[A-Z]\d+$",t):
                    arts.append(article(t,urljoin("https://www.donga.com",a["href"])))
            if arts:
                pages.append({"key":f"{ed}{num}","label":f"{ed}{num}","edition":ed,"number":num,"section":"지면","articles":arts})

    pages.sort(key=lambda x:(x["edition"],x["number"]))
    return {"id":"donga","name":"동아일보","date":date,"status":"자동 수집 완료" if pages else "지면 파싱 실패","source":url,"pages":pages,
            "message":"" if pages else "동아일보 지면 구조가 변경되었을 수 있습니다."}

def collect_mk_section(date,section):
    ymd=date.replace("-","")
    url=f"https://www.mk.co.kr/today-paper/?date={ymd}&section={section}"
    soup=BeautifulSoup(fetch(url).text,"html.parser")
    pages=[]
    seen=set()
    # h2 기준으로 현재 구조를 파싱
    for h in soup.find_all(["h2","h3"]):
        m=re.fullmatch(r"(\d+)면",clean(h.get_text(" ",strip=True)))
        if not m: continue
        num=int(m.group(1)); key=f"{section}{num}"
        if key in seen: continue
        section_name=""
        arts=[]
        # 다음 h2 전까지 형제 영역 수집
        node=h
        steps=0
        while True:
            node=node.find_next()
            steps+=1
            if not node or steps>120: break
            if node.name in ["h2","h3"] and re.fullmatch(r"\d+면",clean(node.get_text(" ",strip=True))): break
            if not section_name and node.name in ["p","strong","span","div"]:
                t=clean(node.get_text(" ",strip=True))
                if 1<=len(t)<=40 and "면" not in t and not re.search(r"기자$",t):
                    section_name=t
            if node.name=="a" and node.get("href"):
                t=clean(node.get_text(" ",strip=True))
                if len(t)>=5 and t not in [x["title"] for x in arts]:
                    href=urljoin("https://www.mk.co.kr",node["href"])
                    # 메뉴/네비게이션 제외
                    if t not in {"제일 위로","맨 위로 이동","더보기","지면뷰어로 보기"}:
                        arts.append(article(t,href))
        if arts:
            seen.add(key)
            pages.append({"key":key,"label":f"{num}면","edition":section,"number":num,"section":section_name or "지면","articles":arts[:25]})
    return pages,url

def collect_mk(date):
    all_pages=[]; source=""
    for sec in ["A","B","C"]:
        try:
            pages,url=collect_mk_section(date,sec)
            if pages: all_pages.extend(pages)
            if not source: source=url
        except requests.HTTPError:
            pass
    # 중복 제거
    uniq={}
    for p in all_pages: uniq[p["key"]]=p
    pages=sorted(uniq.values(), key=lambda x:(x["edition"],x["number"]))
    return {"id":"mk","name":"매일경제","date":date,"status":"자동 수집 완료" if pages else "비발행일 또는 파싱 실패",
            "source":source or "https://www.mk.co.kr/today-paper/","pages":pages,
            "message":"" if pages else "해당 날짜 지면이 없거나 사이트 구조가 변경되었을 수 있습니다."}

def placeholders(date):
    return [
      {"id":"hani","name":"한겨레","date":date,"status":"구독/로그인 기반","source":"https://newsviews.hani.co.kr/","pages":[],"message":"공개 접근 범위 내 연동 방식 검토 중입니다."},
      {"id":"khan","name":"경향신문","date":date,"status":"유료 지면보기","source":"https://epaper.khan.co.kr/","pages":[],"message":"공개 접근 범위 내 연동 방식 검토 중입니다."},
      {"id":"hankyung","name":"한국경제","date":date,"status":"연동 예정","source":"https://www.hankyung.com/","pages":[]},
      {"id":"chosun","name":"조선일보","date":date,"status":"연동 예정","source":"https://www.chosun.com/","pages":[]},
      {"id":"joongang","name":"중앙일보","date":date,"status":"연동 예정","source":"https://www.joongang.co.kr/","pages":[]},
      {"id":"seoul","name":"서울신문","date":date,"status":"연동 예정","source":"https://www.seoul.co.kr/","pages":[]},
    ]

def build(date):
    papers=[]
    for fn in [collect_donga,collect_mk]:
        try:
            papers.append(fn(date))
        except Exception as e:
            name="동아일보" if fn is collect_donga else "매일경제"
            pid="donga" if fn is collect_donga else "mk"
            source="https://www.donga.com/news/Pdf" if pid=="donga" else "https://www.mk.co.kr/today-paper/"
            papers.append({"id":pid,"name":name,"date":date,"status":f"수집 오류: {type(e).__name__}","source":source,"pages":[],"message":"자동 수집 중 오류가 발생했습니다."})
    papers.extend(placeholders(date))
    return {"generated_at":datetime.now(KST).isoformat(),"papers":papers}

def main():
    DATA.mkdir(exist_ok=True)
    today=datetime.now(KST).date()
    # 오늘 + 최근 14일을 유지: 날짜 선택 가능, 누락된 날도 다시 수집
    dates=[(today-timedelta(days=i)).isoformat() for i in range(15)]
    latest=None
    for d in dates:
        payload=build(d)
        (DATA/f"{d}.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
        if d==dates[0]: latest=payload
        print(d, [(p["name"],len(p["pages"])) for p in payload["papers"][:2]])
    (DATA/"latest.json").write_text(json.dumps(latest,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    main()
