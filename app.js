const $ = (s) => document.querySelector(s);
let DB = null;
let selectedPaper = "donga";
let selectedPage = null;
let selectedEdition = "A";
let hideAds = true;

function fmtDate(v) {
  if (!v) return "";
  const d = new Date(v + "T00:00:00");
  return new Intl.DateTimeFormat("ko-KR", {
    year:"numeric", month:"long", day:"numeric", weekday:"long"
  }).format(d);
}

function currentPaper() {
  return DB.papers.find(p => p.id === selectedPaper);
}

function availablePages(paper) {
  let pages = paper.pages || [];
  if (pages.some(p => p.edition_section)) {
    pages = pages.filter(p => (p.edition_section || "A") === selectedEdition);
  }
  if (hideAds) pages = pages.filter(p => !p.is_ad);
  return pages;
}

function ensureSelection() {
  const paper = currentPaper();
  const editions = [...new Set((paper.pages || []).map(p => p.edition_section).filter(Boolean))];
  if (editions.length && !editions.includes(selectedEdition)) selectedEdition = editions[0];

  const pages = availablePages(paper);
  if (!pages.some(p => p.label === selectedPage)) {
    selectedPage = pages[0]?.label ?? null;
  }
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
      selectedEdition = "A";
      selectedPage = null;
      render();
    };
    host.appendChild(b);
  });
}

function renderExtraControls(paper) {
  let host = document.querySelector("#editionControls");
  if (!host) {
    host = document.createElement("div");
    host.id = "editionControls";
    host.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:18px 0 4px;";
    $("#pageTabs").before(host);
  }
  host.innerHTML = "";

  const editions = [...new Set((paper.pages || []).map(p => p.edition_section).filter(Boolean))];
  if (editions.length > 1) {
    editions.forEach(ed => {
      const b = document.createElement("button");
      b.className = "page-tab" + (ed === selectedEdition ? " active" : "");
      b.textContent = `${ed}섹션`;
      b.onclick = () => { selectedEdition = ed; selectedPage = null; render(); };
      host.appendChild(b);
    });
  }

  if ((paper.pages || []).some(p => p.is_ad)) {
    const b = document.createElement("button");
    b.className = "page-tab";
    b.textContent = hideAds ? "광고면 숨김 ✓" : "광고면 표시";
    b.onclick = () => { hideAds = !hideAds; selectedPage = null; render(); };
    host.appendChild(b);
  }
}

function render() {
  renderPapers();
  ensureSelection();
  const paper = currentPaper();

  $("#paperStatus").textContent = paper.status;
  $("#editionDate").textContent = fmtDate(paper.date);
  $("#editionTitle").textContent = paper.name;
  $("#sourceLink").href = paper.source;

  renderExtraControls(paper);

  const pages = availablePages(paper);
  const pageHost = $("#pageTabs");
  pageHost.innerHTML = "";

  pages.forEach(pg => {
    const key = pg.label || String(pg.number);
    const b = document.createElement("button");
    b.className = "page-tab" + (key === selectedPage ? " active" : "");
    b.textContent = pg.label || `${pg.number}면`;
    b.onclick = () => { selectedPage = key; render(); };
    pageHost.appendChild(b);
  });

  const page = pages.find(pg => (pg.label || String(pg.number)) === selectedPage);
  const list = $("#articleList");

  if (!page) {
    $("#pageMeta").textContent = "현재 자동 수집된 지면 데이터가 없습니다.";
    list.innerHTML = `<div class="empty">신문사 지면보기 링크에서 확인할 수 있어요.</div>`;
    return;
  }

  $("#pageMeta").textContent =
    `${page.label || page.number + "면"} · ${page.section || "지면"} · ${page.articles.length}개 항목`;

  if (!page.articles.length) {
    list.innerHTML = `<div class="empty">${page.is_ad ? "전면광고 지면입니다." : "표시할 기사가 없습니다."}</div>`;
    return;
  }

  list.innerHTML = page.articles.map((a, i) => `
    <article class="article">
      <div class="rank">${String(i+1).padStart(2,"0")}</div>
      <div>
        <h3>${a.title}</h3>
        ${a.summary ? `<p>${a.summary}</p>` : ""}
      </div>
      <a class="read" href="${a.url}" target="_blank" rel="noopener">원문 보기 ↗</a>
    </article>
  `).join("");
}

async function init() {
  const res = await fetch("./data/latest.json", {cache:"no-store"});
  DB = await res.json();
  render();
}
init();
