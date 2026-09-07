
const $ = (s) => document.querySelector(s);
let DB = null;
let selectedPaper = "mk";
let selectedPage = 1;

function fmtDate(v) {
  if (!v) return "";
  const d = new Date(v + "T00:00:00");
  return new Intl.DateTimeFormat("ko-KR", {year:"numeric", month:"long", day:"numeric", weekday:"long"}).format(d);
}

function renderPapers() {
  const host = $("#paperTabs");
  host.innerHTML = "";
  DB.papers.forEach(p => {
    const b = document.createElement("button");
    b.className = "paper-tab" + (p.id === selectedPaper ? " active" : "") + (!p.pages.length ? " disabled" : "");
    b.textContent = p.name;
    b.onclick = () => {
      selectedPaper = p.id;
      selectedPage = p.pages[0]?.number ?? 1;
      render();
    };
    host.appendChild(b);
  });
}

function render() {
  renderPapers();
  const paper = DB.papers.find(p => p.id === selectedPaper);
  $("#paperStatus").textContent = paper.status;
  $("#editionDate").textContent = fmtDate(paper.date);
  $("#editionTitle").textContent = paper.name;
  $("#sourceLink").href = paper.source;

  const pageHost = $("#pageTabs");
  pageHost.innerHTML = "";
  paper.pages.forEach(pg => {
    const b = document.createElement("button");
    b.className = "page-tab" + (pg.number === selectedPage ? " active" : "");
    b.textContent = `${pg.number}면`;
    b.onclick = () => { selectedPage = pg.number; render(); };
    pageHost.appendChild(b);
  });

  const page = paper.pages.find(pg => pg.number === selectedPage);
  const list = $("#articleList");
  if (!page) {
    $("#pageMeta").textContent = "이 신문사는 현재 자동 수집 어댑터를 연결하는 단계입니다.";
    list.innerHTML = `<div class="empty">공식 지면보기는 위 링크에서 바로 확인할 수 있어요.<br>수집 어댑터를 추가하면 면별 기사 목록이 이곳에 표시됩니다.</div>`;
    return;
  }

  $("#pageMeta").textContent = `${page.number}면 · ${page.section} · ${page.articles.length}개 기사`;
  list.innerHTML = page.articles.map((a, i) => `
    <article class="article">
      <div class="rank">${String(i+1).padStart(2,"0")}</div>
      <div>
        <h3>${a.title}</h3>
        <p>${a.summary || ""}</p>
      </div>
      <a class="read" href="${a.url}" target="_blank" rel="noopener">원문 보기 ↗</a>
    </article>
  `).join("");
}

async function init() {
  const res = await fetch("./data/latest.json");
  DB = await res.json();
  $("#date").value = DB.papers.find(p => p.id === selectedPaper)?.date || "";
  $("#date").addEventListener("change", () => {
    alert("MVP에서는 latest.json 한 날짜를 표시합니다. scraper.py를 날짜별 JSON 저장 방식으로 확장하면 과거 날짜 탐색도 가능합니다.");
  });
  render();
}
init();
