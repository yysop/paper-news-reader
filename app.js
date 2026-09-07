
const $ = s => document.querySelector(s);
let DB, selectedPaper = "donga", selectedEdition = null, selectedPage = null;

function fmtDate(v){
  if(!v) return "";
  return new Intl.DateTimeFormat("ko-KR",{year:"numeric",month:"long",day:"numeric",weekday:"long"})
    .format(new Date(v+"T00:00:00"));
}
function paper(){ return DB.papers.find(p=>p.id===selectedPaper); }
function editionsOf(p){ return [...new Set((p.pages||[]).map(x=>x.edition).filter(Boolean))]; }
function pagesOf(p){
  const eds = editionsOf(p);
  if(eds.length && !selectedEdition) selectedEdition = eds[0];
  return (p.pages||[]).filter(x => !eds.length || x.edition===selectedEdition);
}
function ensure(){
  const p=paper(), eds=editionsOf(p);
  if(eds.length && !eds.includes(selectedEdition)) selectedEdition=eds[0];
  const pages=pagesOf(p);
  if(!pages.some(x=>x.key===selectedPage)) selectedPage=pages[0]?.key ?? null;
}
function renderPapers(){
  const host=$("#paperTabs"); host.innerHTML="";
  DB.papers.forEach(p=>{
    const b=document.createElement("button");
    b.className="paper-tab"+(p.id===selectedPaper?" active":"")+(!(p.pages||[]).length?" disabled":"");
    b.textContent=p.name;
    b.onclick=()=>{selectedPaper=p.id;selectedEdition=null;selectedPage=null;render()};
    host.appendChild(b);
  });
}
function render(){
  renderPapers(); ensure();
  const p=paper(), pages=pagesOf(p), eds=editionsOf(p);
  $("#paperStatus").textContent=p.status||"";
  $("#editionDate").textContent=fmtDate(p.date);
  $("#editionTitle").textContent=p.name;
  $("#sourceLink").href=p.source||"#";
  $("#date").value=p.date||"";

  const eh=$("#editionTabs"); eh.innerHTML="";
  if(eds.length>1){
    eds.forEach(ed=>{
      const b=document.createElement("button");
      b.className="page-tab"+(ed===selectedEdition?" active":"");
      b.textContent=`${ed}섹션`;
      b.onclick=()=>{selectedEdition=ed;selectedPage=null;render()};
      eh.appendChild(b);
    });
  }

  const ph=$("#pageTabs"); ph.innerHTML="";
  pages.forEach(pg=>{
    const b=document.createElement("button");
    b.className="page-tab"+(pg.key===selectedPage?" active":"");
    b.textContent=pg.label;
    b.onclick=()=>{selectedPage=pg.key;render()};
    ph.appendChild(b);
  });

  const pg=pages.find(x=>x.key===selectedPage), list=$("#articleList");
  if(!pg){
    $("#pageMeta").textContent="현재 자동 수집된 지면 데이터가 없습니다.";
    list.innerHTML=`<div class="empty">${p.message||"공식 지면보기에서 확인할 수 있어요."}</div>`;
    return;
  }
  $("#pageMeta").textContent=`${pg.label} · ${pg.section||"지면"} · ${pg.articles.length}개 기사`;
  list.innerHTML=pg.articles.map((a,i)=>`
    <article class="article">
      <div class="rank">${String(i+1).padStart(2,"0")}</div>
      <div><h3>${a.title}</h3>${a.summary?`<p>${a.summary}</p>`:""}</div>
      <a class="read" href="${a.url||p.source}" target="_blank" rel="noopener">원문 보기 ↗</a>
    </article>`).join("") || `<div class="empty">표시할 기사가 없습니다.</div>`;
}
async function loadDate(date){
  try{
    const r=await fetch(`./data/${date}.json`,{cache:"no-store"});
    if(!r.ok) throw new Error();
    DB=await r.json();
  }catch{
    const r=await fetch("./data/latest.json",{cache:"no-store"});
    DB=await r.json();
  }
  selectedEdition=null; selectedPage=null; render();
}
async function init(){
  const r=await fetch("./data/latest.json",{cache:"no-store"}); DB=await r.json();
  $("#date").addEventListener("change",e=>loadDate(e.target.value));
  render();
}
init();
