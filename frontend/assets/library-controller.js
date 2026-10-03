/** createLibraryController: explicit state, environment and cross-controller actions. */
function createLibraryController({state, getOptions, callbacks, environment}) {
const {document, window, localStorage, fetch, navigator, location, history, prompt} = environment;
const S = state;
const OPT = new Proxy({}, {get: (_, key) => getOptions()?.[key]});
const { AC_NAME, acCleanId, acDisplay, applyScenarioPreset, ga, modalClose, modalOpen, refreshAircraft, showScreen, showView, sum, track, updateRail, recipe } = callbacks;
// ===================== LIBRARY =====================
function roleIcon(r){return '<svg class="icon"><use href="#i-'+(r.ic||'target')+'"/></svg>'}
const ROLES={
 a2a:{label:"Air-to-Air",c:"var(--a2a)",ic:"plane"},
 strike:{label:"Strike",c:"var(--strike)",ic:"flame"},
 sead:{label:"SEAD",c:"var(--sead)",ic:"radar"},
 cas:{label:"CAS",c:"var(--cas)",ic:"target"},
 carrier:{label:"Carrier",c:"var(--carrier)",ic:"anchor"},
 training:{label:"Training",c:"var(--training)",ic:"gradcap"},
 historic:{label:"Historic",c:"var(--historic)",ic:"clock"},
};
let libState={role:"all",own:false,era:null,crew:"qualified",seed:1,cur:null,module:null,initd:false,aircraft:null};
// EVERY template gets a Library card — the Library is the only home for
// scenarios now (no wizard step), so a template with no hand-written card
// metadata still shows up, with sensible synthesized defaults.
function inferRole(k,v){
  const s=(k+' '+(v.label||'')).toLowerCase();
  if(v.needs_carrier||/carrier|acls|recovery|trap/.test(s)) return 'carrier';
  if(/sead|weasel|dead|sam/.test(s)) return 'sead';
  if(/cap|alert|intercept|defense|sweep|bfm/.test(s)) return 'a2a';
  if(/strike|izlid|bomb/.test(s)) return 'strike';
  if(/cas|jtac|kill box/.test(s)) return 'cas';
  if(/corridor|berlin|historic|'44|1944/.test(s)) return 'historic';
  return 'training';
}
// A card that belongs to a TRACK is not shown loose in the grid — the track
// card is its entry point, and eleven numbered rides scattered through an
// alphabetical grid is not a syllabus. The card itself still exists and still
// builds, so every share link that ever pointed at one keeps working.
function trackOf(k){ const t=(OPT.templates[k]||{}).track; return t&&t.id; }
// A SYLLABUS REACHES THE SHELF AS A PUBLISHED PACK OR NOT AT ALL.
//
// A track used to render its own Library card straight out of `tracks.json`,
// and that card was wrong in both directions:
//
//   NOT published — it advertised a course with no syllabus behind it. The
//     whole-track download does not exist (409), so the card's own note had to
//     tell the pilot to generate eleven rides one at a time. You do not shelve
//     a course you have not published.
//
//   published — `_pack_templates()` ALREADY renders it, with the pinned
//     missions, the version and what he must own. The track card beside it
//     made two cards for one syllabus, and they were not the same missions:
//     the pack's seeds are fixed (4400 + n) so its printed guide stays true,
//     while the track card carries no seed and the server rolls one per
//     request. Same name, same label, different sortie.
//
// Both rules point the same way, so there is nothing to filter — the shelf
// simply does not list tracks. The track itself is untouched: `OPT.tracks`
// still carries every one, `openTrack` reads it directly, and any link that
// ever pointed at `track_<id>` still opens the panel and still builds.
function libItems(){ return (Object.entries(OPT.templates)
  .filter(([k,v])=>v&&!k.startsWith('_')&&!v.quick&&!trackOf(k))
  .map(([k,v])=>{
    const lib=v.library||{};
    const parts=(v.label||k).split(' — ');
    return {k,...v,
      role: lib.role||inferRole(k,v),
      premise: lib.premise||parts[1]||parts[0],
      threat: lib.threat!=null?lib.threat:(v.recipe&&v.recipe.threat_intensity)||1,
      players: lib.players||'SP',
      aircraft: (v.recipe&&v.recipe.aircraft)||null,
      module: lib.module||null,
      // A PAID MODULE THE CARD DEPENDS ON. Not the same thing as the
      // ownership check below: that compares against maps and aircraft
      // the user has ticked, and Supercarrier is neither. It is a boat
      // and a set of radio procedures, so nothing in the ownership
      // picker can answer for it — the honest move is to state it on
      // every card and let the pilot decide, rather than hide the card
      // or let him download a Case III ride with no Marshal in it.
      requires: lib.requires||null,
      kind: v.kind||'open', tasked: !!v.tasked,
      featured: !!lib.featured, new: !!lib.new};
  })); }
// A ride opened from inside a track card: the ordinary template item, fetched
// by key even though the grid does not list it.
function rideItem(k){ const v=OPT.templates[k]; if(!v) return null;
  const lib=v.library||{}, parts=(v.label||k).split(' — ');
  return {k,...v, role:lib.role||'training', premise:lib.premise||parts[1]||parts[0],
    threat:lib.threat!=null?lib.threat:1, players:lib.players||'SP',
    aircraft:(v.recipe&&v.recipe.aircraft)||null, module:lib.module||null,
    requires:lib.requires||null,
    kind:v.kind||'open', tasked:!!v.tasked, featured:false, new:!!lib.new}; }
function ownRow(t){
  if(!ownSetP()) return '';                    // ownership not declared yet
  const req=libReq(t);
  return req
    ? '<div class="ownrow needs"><svg class="icon"><use href="#i-lock"/></svg> Needs: '+reqLabel(req)+'</div>'
    : '<div class="ownrow have">✓ You own the terrain &amp; aircraft</div>';
}
// Short form for badges, chips and the rail: cleaned designation, no name.
function acLabel(key){ if(!key) return null; const a=(OPT.aircraft||[]).find(x=>x.key===key); return a?acCleanId(a.id, AC_NAME[a.key]):key; }
// R1/R2: designation + name, for the filter dropdown and the search haystack.
// Badges and chips keep the short designation so they stay one line.
function acLabelFull(key){ if(!key) return null;
  const a=(OPT.aircraft||[]).find(x=>x.key===key); return a?acDisplay(a.key,a.id):key; }
function mapKeyOf(t){ return t.default_map || (t.maps&&t.maps[0]) || null; }
function mapLabel(mk){ return (OPT.maps[mk]&&OPT.maps[mk].label)||mk; }
function initLibFilters(){
  if(libState.initd) return; libState.initd=true;
  const items=libItems();
  const add=(selId,pairs)=>{const s=document.getElementById(selId);
    pairs.forEach(([k,lab])=>{const o=document.createElement('option');o.value=k;o.textContent=lab;s.appendChild(o);});};
  add('lfAc',[...new Set(items.map(t=>t.aircraft).filter(Boolean))].map(k=>[k,acLabelFull(k)]).sort((a,b)=>a[1].localeCompare(b[1])));
  add('lfMap',[...new Set(items.map(mapKeyOf).filter(Boolean))].map(k=>[k,mapLabel(k)]).sort((a,b)=>a[1].localeCompare(b[1])));
}
function libSort(a,b){
  const s=document.getElementById('lfSort').value;
  const la=libReq(a)?1:0, lb=libReq(b)?1:0;   // owned first, locked sink
  if(la!==lb) return la-lb;
  if(s==='az') return a.label.localeCompare(b.label);
  if(s==='new') return (b.new-a.new)||a.label.localeCompare(b.label);
  if(s==='threat') return (b.threat-a.threat)||a.label.localeCompare(b.label);
  return (b.featured-a.featured)||(b.new-a.new)||a.label.localeCompare(b.label);
}
const MOD_PITCH={
  'F-100D':'“The Hun” — America’s first supersonic fighter-bomber, just released for DCS. Cold-War nuclear alert, battlefield CAS, flak suppression and gunfighter BFM.',
  'F-14B(U)':'The upgraded Tomcat with full crew AI — Jester and Iceman fly your calls on the F10 menu. Outer-air-battle, buddy-lase strike, TARPS recon and the boat.'};
function renderModuleRail(items,anyF){
  const rail=document.getElementById('lmodules');
  if(anyF){ rail.innerHTML=''; return; }
  const mods={}; items.forEach(t=>{ if(t.module)(mods[t.module]=mods[t.module]||[]).push(t); });
  const order=Object.keys(mods).sort();
  if(!order.length){ rail.innerHTML=''; return; }
  let h='<div class="sechead">New in DCS</div><div class="lmodrail">';
  h+=order.map(m=>{ const n=mods[m].length;
    return '<div class="lmodcard" role="button" tabindex="0" onclick="filterModule(\''+m.replace(/'/g,"\\'")+'\')">'+
      '<span class="lmodtag">New module</span><h3>'+m+'</h3>'+
      '<p>'+(MOD_PITCH[m]||'')+'</p>'+
      '<span class="mgo">'+n+' mission'+(n!==1?'s':'')+' &nbsp;→</span></div>'; }).join('');
  rail.innerHTML=h+'</div>';
}
function filterModule(m){ libState.module=m; renderLib(); window.scrollTo(0,0); }
function renderChips(anyF){
  const bar=document.getElementById('lchipbar'); if(!anyF){ bar.innerHTML=''; return; }
  const chips=[];
  if(libState.module) chips.push(['Module',libState.module,"clearModule()"]);
  if(libState.role!=='all') chips.push(['Role',(ROLES[libState.role]||{}).label||libState.role,"setRole('all')"]);
  const g=id=>document.getElementById(id);
  if(g('lfType').value!=='all') chips.push(['Type',g('lfType').options[g('lfType').selectedIndex].text,"clearFilter('lfType')"]);
  if(g('lfAc').value!=='all') chips.push(['Aircraft',acLabel(g('lfAc').value),"clearFilter('lfAc')"]);
  if(g('lfMap').value!=='all') chips.push(['Map',mapLabel(g('lfMap').value),"clearFilter('lfMap')"]);
  if(g('lfEra').value!=='all') chips.push(['Era',g('lfEra').options[g('lfEra').selectedIndex].text,"clearFilter('lfEra')"]);
  if(g('lfDiff').value!=='all') chips.push(['Threat',g('lfDiff').options[g('lfDiff').selectedIndex].text,"clearFilter('lfDiff')"]);
  if(g('lfSearch').value.trim()) chips.push(['Search','“'+g('lfSearch').value.trim()+'”',"clearFilter('lfSearch')"]);
  if(libState.own) chips.push(['','Only what I own',"toggleOwn()"]);
  let h=chips.map(([k,v,fn])=>'<span class="fchip" role="button" tabindex="0" onclick="'+fn+'">'+(k?'<b>'+k+':</b> ':'')+v+' <span class="x">✕</span></span>').join('');
  if(chips.length) h+='<button class="fclear" onclick="clearFilters()">Clear all</button>';
  bar.innerHTML=h;
}
function clearModule(){ libState.module=null; renderLib(); }
function clearFilter(id){ const e=document.getElementById(id); if(e.type==='search') e.value=''; else e.value='all'; renderLib(); }
function clearFilters(){ libState.role='all'; libState.own=false; libState.module=null;
  document.getElementById('lown').classList.remove('on');
  ['lfType','lfAc','lfMap','lfEra','lfDiff'].forEach(i=>document.getElementById(i).value='all');
  document.getElementById('lfSearch').value=''; document.getElementById('lfSort').value='featured';
  buildRoleTabs(); renderLib(); }
// ---- ownership: the user declares which maps + modules they own (stored on
// this device). Until they do, nothing is locked. Free content is always owned.
const BASE_AC=new Set(['Su_25T','TF_51D']);   // ship free with DCS
function ownStore(){ try{return JSON.parse(localStorage.getItem('ms_owned')||'null')}catch(e){return null} }
function ownSetP(){ const o=ownStore(); return !!(o&&o.set); }
function ownedMaps(){ const o=ownStore(); if(!(o&&o.set)) return null;   // null = treat all as owned
  const free=Object.keys(OPT.maps).filter(k=>OPT.maps[k].free);
  return new Set([...free,...(o.maps||[])]); }
function ownedAc(){ const o=ownStore(); if(!(o&&o.set)) return null;
  return new Set([...BASE_AC,...(o.aircraft||[])]); }
// returns {map,ac} of what a mission needs but the user doesn't own, or null
function libReq(t){
  const om=ownedMaps(), oa=ownedAc(); const mk=mapKeyOf(t);
  let mReq=(om&&mk&&!om.has(mk))?mapLabel(mk):null;
  let aReq=(oa&&t.aircraft&&!oa.has(t.aircraft))?acLabel(t.aircraft):null;
  return (mReq||aReq)?{map:mReq,ac:aReq}:null;
}
function reqLabel(req){ return [req.ac,req.map].filter(Boolean).join(' · '); }
function thrBar(n){ let s='<span class="thr">'; for(let i=1;i<=5;i++)s+='<i class="'+(i<=n?'f'+n:'')+'"></i>'; return s+'</span>'; }
function eraLabels(er){ return (er||[]).map(e=>OPT.eras[e]?OPT.eras[e].label:e).join(' · '); }

function buildRoleTabs(){
  const present=new Set(libItems().map(t=>t.role));
  const order=['a2a','strike','sead','cas','carrier','training','historic'];
  let h='<button class="rtab '+(libState.role==='all'?'on':'')+'" onclick="setRole(\'all\')">All</button>';
  for(const k of order) if(present.has(k)) h+='<button class="rtab '+(libState.role===k?'on':'')+
    '" onclick="setRole(\''+k+'\')"><span class="rc" style="background:'+ROLES[k].c+'"></span>'+ROLES[k].label+'</button>';
  document.getElementById('roletabs').innerHTML=h;
}
function setRole(r){ libState.role=r; buildRoleTabs(); renderLib(); }
function toggleOwn(){
  if(!ownSetP()){ openOwn(); return; }   // first use: pick what you own
  libState.own=!libState.own; const _sw=document.getElementById('lown');
  _sw.classList.toggle('on',libState.own); _sw.setAttribute('aria-checked',String(libState.own)); renderLib(); }
// ---- "what I own" editor ----
// nickname aliases so simmers can search by callsign, not designation
const OWN_ALIAS={
  'FA_18C_hornet':'hornet bug','F_16C_50':'viper falcon','F_15E':'strike eagle mudhen',
  'F_15ESE':'strike eagle','F_14B':'tomcat','F_14A_135_GR':'tomcat','F_14A_135_GR_Early':'tomcat',
  'F_14A_95_GR':'tomcat','F_14B_U':'tomcat bombcat','A_10C_2':'warthog hog','A_10C':'warthog hog',
  'A_10A':'warthog hog','AV8BNA':'harrier','JF_17':'thunder','M_2000C':'mirage 2000',
  'Mirage_F1CE':'mirage f1','Mirage_F1EE':'mirage f1','MiG_29A':'fulcrum','MiG_29S':'fulcrum',
  'MiG_29G':'fulcrum','Su_27':'flanker','Su_33':'flanker','MiG_21Bis':'fishbed','F_4E_45MC':'phantom',
  'F_5E_3':'tiger','F_86F_35':'sabre','A_4E_C':'skyhawk','AH_64D_BLK_II':'apache','Ka_50_3':'blackshark',
  'Ka_50':'blackshark','Mi_24P':'hind','Mi_8MT':'hip','UH_1H':'huey','SA342M':'gazelle',
  'P_51D':'mustang','P_51D_30_NA':'mustang','SpitfireLFMkIX':'spitfire','P_47D_30':'thunderbolt jug',
  'Bf_109K_4':'messerschmitt','FW_190D9':'butcher bird','F_100D':'hun super sabre','A6E':'intruder',
  'persiangulf':'gulf hormuz','thechannel':'channel','falklands':'south atlantic malvinas',
  'nevada':'nttr nellis','marianas':'guam mariana','germany':'fulda igb inner german',
  'afghanistan':'afghan','syria':'levant'};
function ownCats(){
  const maps=Object.entries(OPT.maps).map(([k,v])=>({key:k,label:v.label,free:!!v.free}));
  const byCat={modern:[],coldwar:[],wwii:[],helo:[]};
  (OPT.aircraft||[]).forEach(a=>{ if(BASE_AC.has(a.key))return;
    let c; const from=(a.service&&a.service[0])||9999;
    if(a.kind==='helicopter')c='helo'; else if(from<=1945)c='wwii'; else if(from>=1975)c='modern'; else c='coldwar';
    byCat[c].push({key:a.key,label:a.id}); });
  const s=arr=>arr.sort((x,y)=>x.label.localeCompare(y.label));
  return [
    {kind:'maps',id:'terrains',title:'Terrains',items:s(maps)},
    {kind:'aircraft',id:'modern',title:'Modern jets',items:s(byCat.modern)},
    {kind:'aircraft',id:'coldwar',title:'Cold War jets',items:s(byCat.coldwar)},
    {kind:'aircraft',id:'wwii',title:'WWII warbirds',items:s(byCat.wwii)},
    {kind:'aircraft',id:'helo',title:'Helicopters',items:s(byCat.helo)}];
}
function ownMatch(it,q){ if(!q)return true; q=q.toLowerCase();
  return (it.label||'').toLowerCase().includes(q)||(OWN_ALIAS[it.key]||'').toLowerCase().includes(q)||it.key.toLowerCase().includes(q); }
let ownEdit=null;
function openOwn(){ const o=ownStore();
  ownEdit={maps:new Set((o&&o.maps)||[]), aircraft:new Set((o&&o.aircraft)||[])};
  const h='<button class="dclose" onclick="closeOwn()">×</button>'+
    '<div class="eyebrow" style="margin-bottom:6px">My DCS install</div>'+
    '<h2 style="margin:0 0 4px;font-size:24px">What do you own?</h2>'+
    '<p class="dprem" style="font-size:13.5px">Tick your terrains and aircraft — search by name or nickname (Hornet, Warthog, Fulda…), or Select all per category. Saved on this device only; free content is always included.</p>'+
    '<div class="osearch"><span class="lsi"><svg class="icon"><use href="#i-search"/></svg></span><input id="ownsearch" type="search" aria-label="Search modules" placeholder="Search modules — e.g. Hornet, Syria, Apache…" oninput="renderOwnBody()" autocomplete="off"></div>'+
    '<div id="ownbody" class="ownbody"></div>'+
    '<div class="dcta"><span id="ownfoot" style="align-self:center;color:var(--dim);font-size:12px;margin-right:auto"></span>'+
    '<button class="prime" onclick="saveOwn()">Save</button></div>';
  document.getElementById('ocardinner').innerHTML=h;
  renderOwnBody(); document.getElementById('ownmodal').classList.add('on');
  modalOpen(document.getElementById('ownmodal'));
}
function closeOwn(){ document.getElementById('ownmodal').classList.remove('on'); modalClose(); }
function toggleOwnItem(kind,key){ const s=ownEdit[kind]; s.has(key)?s.delete(key):s.add(key); renderOwnBody(); }
function ownSelectAll(kind,id){ (ownCats().find(c=>c.id===id)||{items:[]}).items.forEach(it=>{ if(!it.free) ownEdit[kind].add(it.key); }); renderOwnBody(); }
function ownClearCat(kind,id){ (ownCats().find(c=>c.id===id)||{items:[]}).items.forEach(it=>ownEdit[kind].delete(it.key)); renderOwnBody(); }
function renderOwnBody(){
  const q=(document.getElementById('ownsearch').value||'').trim();
  let h='';
  ownCats().forEach(c=>{
    const set=ownEdit[c.kind], items=c.items.filter(it=>ownMatch(it,q));
    const ownedN=c.items.filter(it=>set.has(it.key)||it.free).length;
    h+='<div class="ocat"><div class="ocathead"><h4>'+c.title+' <span class="ocount">'+ownedN+' owned</span></h4>'+
       '<div class="ocatbtns"><button class="osel" onclick="ownSelectAll(\''+c.kind+'\',\''+c.id+'\')">Select all</button>'+
       '<button class="oclr" onclick="ownClearCat(\''+c.kind+'\',\''+c.id+'\')">Clear</button></div></div>';
    h+= items.length
      ? '<div class="ogrid">'+items.map(it=>{ const on=set.has(it.key)||it.free;
          return '<div class="ochk'+(on?' on':'')+(it.free?' fixed':'')+'"'+
            (it.free?'':' role="checkbox" tabindex="0" aria-checked="'+(on?'true':'false')+'"'
             +' onclick="toggleOwnItem(\''+c.kind+'\',\''+it.key+'\')"')+'>'+
            '<span class="ck">'+(on?'✓':'')+'</span>'+it.label+(it.free?' <span class="ofree">free</span>':'')+'</div>';
        }).join('')+'</div>'
      : '<div class="onone">No matches</div>';
    h+='</div>';
  });
  document.getElementById('ownbody').innerHTML=h;
  const fc=document.getElementById('ownfoot');
  if(fc) fc.textContent=(ownEdit.maps.size+ownEdit.aircraft.size)+' modules marked owned';
}
function saveOwn(){ ownSet_({set:true, maps:[...ownEdit.maps], aircraft:[...ownEdit.aircraft]});
  libState.own=true; document.getElementById('lown').classList.add('on'); closeOwn(); renderLib(); }
function ownSet_(o){ try{localStorage.setItem('ms_owned',JSON.stringify(o))}catch(e){} }
function libCard(t){
  const r=ROLES[t.role]||ROLES.training, req=libReq(t), locked=libState.own&&req;
  // pack cards with cover art (the NATC seal on AWI Basics) get a media
  // header — the one place a Library card earns an image
  const media = (t.pack&&t.pack.image)
    ? '<div class="lmedia"><img src="/api/pack/'+t.pack.id+'/'+t.pack.image+'" alt=""> '+
      '<span class="lmcount">'+((t.pack.events||[]).length||1)+' MISSIONS</span></div>' : '';
  // A track wears its length on the card. "Eleven rides in order" is the
  // whole proposition, and burying it in the modal loses the argument.
  const tbadge = t.track
    ? '<span class="lchip"><svg class="icon"><use href="#i-clipboard"/></svg> '+
      t.track.rides.length+'-ride track</span>' : '';
  return '<div class="libcard'+(locked?' locked':'')+'" role="button" tabindex="0" onclick="openDetail(\''+t.k+'\')">'+
    '<div class="bar" style="background:'+r.c+'"></div>'+media+
    (t.new?'<span class="lnew">NEW</span>':'')+(req?'<span class="lreq"><svg class="icon"><use href="#i-lock"/></svg> '+reqLabel(req)+'</span>':'')+
    '<div class="cbody"><div class="rt"><div class="ric" style="background:'+r.c+'22">'+roleIcon(r)+'</div>'+
      '<div class="role" style="color:'+r.c+'">'+r.label+'</div>'+
      '<span class="kindb '+(t.kind==='full'?'full':'open')+'">'+(t.kind==='full'?'FULL MISSION':'OPEN STARTER')+'</span></div>'+
      '<h3>'+(t.title||t.label.split(' —')[0])+'</h3><p class="prem">'+(t.premise||'')+'</p>'+
      '<div class="lchips">'+tbadge+
        (t.aircraft?'<span class="acbadge"><svg class="icon"><use href="#i-plane"/></svg> '+acLabel(t.aircraft)+'</span>':'')+
        '<span class="lchip">'+eraLabels(t.eras)+'</span>'+
        '<span class="lchip">'+thrBar(t.threat||1)+'</span>'+
        '<span class="lchip">'+(t.players||'SP')+'</span>'+
        (t.tasked?'<span class="lchip"><svg class="icon"><use href="#i-clipboard"/></svg> Tasking brief</span>':'')+
        (t.needs_carrier?'<span class="lchip"><svg class="icon"><use href="#i-anchor"/></svg> Carrier</span>':'')+
        (t.requires?'<span class="lchip needsmod"><svg class="icon"><use href="#i-lock"/></svg> Requires '+t.requires+'</span>':'')+'</div>'+
      ownRow(t)+
    '</div></div>';
}
function libPasses(t){
  if(libState.module&&t.module!==libState.module) return false;
  if(libState.role!=='all'&&t.role!==libState.role) return false;
  const ty=document.getElementById('lfType').value; if(ty!=='all'&&(t.kind||'open')!==ty) return false;
  const e=document.getElementById('lfEra').value; if(e!=='all'&&!(t.eras||[]).includes(e)) return false;
  const d=document.getElementById('lfDiff').value, th=t.threat||1;
  if(d==='lo'&&th>2) return false; if(d==='md'&&th!==3) return false; if(d==='hi'&&th<4) return false;
  const ac=document.getElementById('lfAc').value; if(ac!=='all'&&t.aircraft!==ac) return false;
  const mp=document.getElementById('lfMap').value; if(mp!=='all'&&mapKeyOf(t)!==mp) return false;
  const q=(document.getElementById('lfSearch').value||'').trim().toLowerCase();
  // R2: simmers search by callsign ("Warthog", "Viper"), not by DCS type id.
  // Fold in the popular name AND the nickname list the "What do you own?" modal
  // already used, so the same words work everywhere in the app.
  // acLabelFull is the cleaned designation; keep the raw type id in the haystack
  // too so anyone pasting "FA-18C_hornet" out of a .miz still gets a hit.
  if(q){ const hay=((t.label||'')+' '+(t.premise||'')+' '+(acLabelFull(t.aircraft)||'')+' '+
    (((OPT.aircraft||[]).find(x=>x.key===t.aircraft)||{}).id||'')+' '+
    (OWN_ALIAS[t.aircraft]||'')+' '+(OWN_ALIAS[mapKeyOf(t)]||'')+' '+(mapKeyOf(t)?mapLabel(mapKeyOf(t)):'')+' '+
    (t.module||'')+' '+((ROLES[t.role]||{}).label||'')).toLowerCase();
    if(!hay.includes(q)) return false; }
  if(libState.own&&libReq(t)) return false;
  return true;
}
function renderLib(){
  initLibFilters();
  const items=libItems(), g=id=>document.getElementById(id);
  const anyF=libState.module||libState.role!=='all'||g('lfEra').value!=='all'||g('lfDiff').value!=='all'||
    g('lfType').value!=='all'||g('lfAc').value!=='all'||g('lfMap').value!=='all'||g('lfSearch').value.trim()||libState.own;
  renderModuleRail(items,anyF);
  g('lfeatwrap').style.display=anyF?'none':'';
  g('lallhead').textContent=anyF?'Results':'All missions';
  g('lfeat').innerHTML=items.filter(t=>t.featured).sort(libSort).map(libCard).join('');
  const list=items.filter(libPasses).sort(libSort);
  g('lgrid').innerHTML=list.length?list.map(libCard).join(''):
    '<div class="lempty">No missions match those filters. Loosen a filter, clear the search, or switch to <b>Build</b> to make one from scratch.</div>';
  g('libcount').textContent=list.length+' mission'+(list.length!==1?'s':'');
  renderChips(anyF);
}
function inclLines(t){
  const rc=t.recipe||{}, L=[];
  if(t.needs_carrier||rc.bb_carrier) L.push('Carrier strike group — measured deck, recovery + support');
  if((t.threat||0)>=3||(rc.threat_intensity||0)>=3) L.push('Doctrinal SAM/air threats tuned to the difficulty');
  else L.push('Light, era-correct defenses');
  if(rc.bb_tanker!==false) L.push('Tanker on station with TACAN / frequency');
  if(rc.bb_awacs) L.push('AWACS picture on the threat axis');
  L.push('Bullseye, nav references and F10 map overlays');
  if(t.aircraft_locked) L.push('Crew-ops flight — the AI back-seater flies your calls');
  L.push('Opens in the DCS editor — tweak anything after');
  return L;
}
// A card that offers a SET of airframes (formation training) rather than
// pinning one. Falls back to the card's by_era/recipe pin, so cards without
// aircraft_choices behave exactly as before.
function acChoices(t, era){ return ((t.aircraft_choices||{})[era])||[]; }
function acDefaultFor(t, era){
  return ((t.by_era||{})[era]||{}).aircraft || (t.recipe||{}).aircraft || null;
}
function acChoiceRow(t){
  const era=libState.era, list=acChoices(t, era);
  if(!list.length) return '';
  // Only offer aircraft the roster actually knows about, so a data typo drops
  // one button instead of handing the engine an unbuildable key.
  const known=list.filter(key=>(OPT.aircraft||[]).some(a=>a.key===key));
  if(!known.length) return '';
  return known.map(key=>'<button class="pbtn '+(key===libState.aircraft?'on':'')+
    '" onclick="pickAircraft(\''+key+'\')">'+(acLabel(key)||key)+'</button>').join('');
}
function acChoiceBlock(t){
  if(!acChoices(t, libState.era).length) return '';
  return '<div class="dblock"><h4>Aircraft — lead flies the same type</h4>'+
    '<div class="pillrow" id="dAcRow">'+acChoiceRow(t)+'</div></div>';
}
function pickAircraft(key){
  libState.aircraft=key;
  const t=libFind(libState.cur); if(!t) return;
  const row=document.getElementById('dAcRow'); if(row) row.innerHTML=acChoiceRow(t);
}
function libFind(k){ return libItems().find(x=>x.k===k) || rideItem(k); }
// The track card: the syllabus in flying order, one row per ride, each row a
// button that opens that ride's ordinary card. Plus the two downloads Rob
// asked for — the whole track as one zip, and the printed guide.
// =============================================================== THE PIPELINE
// Three schools laid over the tracks and cards (missiongen/courses.py). The
// page is the student's view: pick a course, open a school, tick units as
// you fly them to the standard on their brief. The tick is localStorage —
// this browser, nobody else — which is the same privacy line the analytics
// draw. A squadron takes the kit instead.
function esc(x){ return String(x==null?'':x).replace(/[&<>"']/g, ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
const pipeState={course:null, school:null, data:{}};
function pKey(cid){ return 'ss_course_'+cid; }
function pProgress(cid){ try{ return JSON.parse(localStorage.getItem(pKey(cid))||'{}'); }catch(e){ return {}; } }
function pSetDone(cid, uid, on){
  const pr=pProgress(cid); if(on) pr[uid]=Date.now(); else delete pr[uid];
  try{ localStorage.setItem(pKey(cid), JSON.stringify(pr)); }catch(e){}
  ga('pipeline_unit', {course: cid, unit: uid, done: !!on});
  renderPipeline();
}
function pSchoolStats(c, sc, pr){
  const units=sc.phases.flatMap(p=>p.units).filter(u=>u.status==='ready');
  const done=units.filter(u=>pr[u.uid]).length;
  return {n:units.length, done:done, pct: units.length? Math.round(100*done/units.length):0};
}
async function renderPipeline(){
  const list=OPT.courses||{};
  const ids=Object.keys(list);
  document.getElementById('pcount').textContent=ids.length+(ids.length===1?' course':' courses');
  if(!pipeState.course) pipeState.course=ids[0]||null;
  const cid=pipeState.course;
  if(!cid){ document.getElementById('pcourses').innerHTML='<p class="dprem">No courses published yet.</p>'; return; }
  if(!pipeState.data[cid]){
    try{ pipeState.data[cid]=await (await fetch('/api/course/'+encodeURIComponent(cid))).json(); }
    catch(e){ document.getElementById('pbody').innerHTML='<p class="dprem">The course could not be loaded.</p>'; return; }
  }
  const c=pipeState.data[cid], pr=pProgress(cid);
  const all=c.schools.flatMap(sc=>sc.phases.flatMap(p=>p.units)).filter(u=>u.status==='ready');
  const done=all.filter(u=>pr[u.uid]).length;
  document.getElementById('pcourses').innerHTML=
    '<div class="pcourse">'+
      '<div class="eyebrow" style="margin-bottom:6px">Training course · '+esc(c.module||'')+' · '+esc((OPT.eras[c.era]||{}).label||c.era||'')+'</div>'+
      '<h2>'+esc(c.label)+'</h2><p class="dprem">'+esc(c.premise)+'</p>'+
      '<p class="dprem" style="font-size:13.5px">'+esc((c.blurb||[]).join(' '))+'</p>'+
      '<div class="pstats">'+
        '<span class="lchip">'+c.counts.rides+' rides</span>'+
        '<span class="lchip">'+c.counts.readings+' readings</span>'+
        '<span class="lchip">'+c.counts.planned+' planned — shown, not hidden</span>'+
        '<span class="lchip">Your record: '+done+' / '+all.length+' units done (this browser only)</span>'+
      '</div>'+
      '<div class="dcta" style="margin-top:6px">'+
        '<a class="ghost" style="text-decoration:none;text-align:center" href="/api/course/'+encodeURIComponent(cid)+'/kit.zip" download onclick="ga(\'pipeline_kit\',{course:\''+cid+'\'})"><svg class="icon"><use href="#i-download"/></svg> Squadron kit — program, gradesheet, readings</a>'+
        '<button class="ghost" onclick="openReading(\''+cid+'\',\'pipeline_howto\')"><svg class="icon"><use href="#i-book"/></svg> How this pipeline works</button>'+
        (done?'<button class="ghost" onclick="if(confirm(\'Clear your record for this course in this browser?\')){localStorage.removeItem(pKey(\''+cid+'\'));renderPipeline();}">Reset my record</button>':'')+
      '</div>'+
    '</div>'+
    '<div class="pschools">'+c.schools.map(sc=>{
      const st=pSchoolStats(c, sc, pr);
      return '<div class="pschool '+(pipeState.school===sc.id?'on':'')+'" role="button" tabindex="0" onclick="pipeState.school=\''+sc.id+'\';renderPipeline()" onkeydown="if(event.key===\'Enter\'||event.key===\' \'){this.click();event.preventDefault();}">'+
        '<div class="sn">School '+sc.n+(sc.module_agnostic?' · any jet':'')+'</div><h3>'+esc(sc.label)+'</h3>'+
        '<div class="tag">'+esc(sc.tagline)+'</div>'+
        '<div class="pbar"><i style="width:'+st.pct+'%"></i></div>'+
        '<div class="pbarlbl">'+st.done+' / '+st.n+' units · '+sc.phases.length+' phases</div></div>';
    }).join('')+'</div>';
  if(!pipeState.school) pipeState.school=c.schools[0].id;
  const sc=c.schools.find(x=>x.id===pipeState.school)||c.schools[0];
  const pref={aircraft:c.aircraft, era:c.era};
  document.getElementById('pbody').innerHTML=
    '<div class="pcourse">'+
      '<div class="eyebrow" style="margin-bottom:6px">School '+sc.n+' of '+c.schools.length+(sc.requires_school?' · after School '+(c.schools.find(x=>x.id===sc.requires_school)||{}).n:'')+'</div>'+
      '<h2>'+esc(sc.label)+'</h2><p class="dprem">'+esc(sc.intro||'')+'</p>'+
      sc.phases.map((ph,pi)=>
        '<div class="pphase"><div class="sechead">Phase '+(pi+1)+' · '+esc(ph.label)+'</div>'+
        (ph.intro?'<div class="intro">'+esc(ph.intro)+'</div>':'')+
        ph.units.map(u=>unitRow(c, u, pr, pref)).join('')+'</div>').join('')+
    '</div>';
}
function unitRow(c, u, pr, pref){
  const isDone=!!pr[u.uid], ready=u.status==='ready';
  const chk=ready?'<input class="uchk" type="checkbox" '+(isDone?'checked':'')+' aria-label="Done" onchange="pSetDone(\''+c.id+'\',\''+u.uid+'\',this.checked)">'
                 :'<span class="uchk" aria-hidden="true"></span>';
  let kind='', sub='', act='';
  const pa=JSON.stringify({aircraft:pref.aircraft, era:pref.era}).replace(/"/g,'&quot;');
  if(u.kind==='reading'){ kind='Reading'; sub=(u.minutes?u.minutes+' min':'');
    act='<a class="ub" href="#" onclick="openReading(\''+c.id+'\',\''+u.doc+'\');return false">Read</a>'; }
  else if(u.kind==='track'){ kind=u.check?'Check ride':(u.rides+(u.rides===1?' ride':' rides')); sub=u.premise+(u.requires?' · Requires '+u.requires:'');
    act='<a class="ub" href="#" onclick="openTrack(\''+u.track+'\','+pa+');return false">Open track</a>'; }
  else if(u.kind==='card'){ kind=u.check?'Check ride':'1 ride'; sub=u.premise;
    act='<a class="ub" href="#" onclick="openDetail(\''+u.key+'\','+pa+');return false">Open</a>'; }
  else { kind='Planned'; sub=u.why; }
  const graded = ready&&u.kind!=='reading' ? (u.graded?'<span class="uk">graded in-mission</span>':'<span class="uk">IP grades</span>') : '';
  return '<div class="unit '+(isDone?'done':'')+(ready?'':' planned')+'">'+chk+
    '<div class="ut">'+esc(u.label)+(sub?'<small>'+esc(sub)+'</small>':'')+'</div>'+
    '<span class="uk">'+esc(kind)+'</span>'+graded+act+'</div>';
}
async function openReading(cid, doc){
  let r; try{ r=await (await fetch('/api/course/'+encodeURIComponent(cid)+'/reading/'+encodeURIComponent(doc))).json(); }catch(e){ return; }
  ga('pipeline_reading', {course: cid, doc: doc});
  document.getElementById('dcardinner').innerHTML=
    '<button class="dclose" onclick="closeDetail()">×</button>'+
    '<div class="reading"><div class="eyebrow" style="margin-bottom:6px">Reading · '+esc((OPT.courses[cid]||{}).short||cid)+'</div>'+
    r.html+'</div>';
  document.getElementById('libdetail').classList.add('on');
  modalOpen(document.getElementById('libdetail'));
  syncGenerationButtons();
}
function openTrack(id, pref){
  const tr=(OPT.tracks||{})[id]; if(!tr) return;
  ga('track_open', {track: id});
  const pk=tr.picker||{};
  // Seed the wizard with the track's own defaults where they are legal, and
  // with the first working combination where they are not — so the panel is
  // never in a state that cannot be downloaded. The pipeline may prefer a
  // combination (the course's jet and era); it is used only where legal.
  let era=(pk[tr.eras&&tr.eras[0]]?tr.eras[0]:Object.keys(pk)[0]);
  if(pref&&pref.era&&pk[pref.era]) era=pref.era;
  trackState={id:id, era:era,
              ac:(pk[era]&&pk[era][tr.aircraft])?tr.aircraft:Object.keys(pk[era]||{})[0]};
  if(pref&&pref.aircraft&&pk[era]&&pk[era][pref.aircraft]) trackState.ac=pref.aircraft;
  trackState.tk=trackPick(pk,trackState).includes(tr.tanker)?tr.tanker:trackPick(pk,trackState)[0];
  document.getElementById('dcardinner').innerHTML=
    '<button class="dclose" onclick="closeDetail()">×</button>'+
    '<div class="eyebrow" style="margin-bottom:6px">Training track · '+(tr.service||'')+'</div>'+
    '<h2>'+tr.label+'</h2><p class="dprem">'+tr.premise+'</p>'+
    // THE PAID MODULE, ABOVE THE FOLD. A Case III track without Supercarrier
    // is a boat that does not answer the radio, and the pilot reads that as
    // our bug. Said here as well as on each ride's card, because the track
    // panel is where somebody decides to download eleven megabytes.
    (tr.requires?'<p class="dprem" style="font-size:13px;color:var(--amber)">'+
      'Requires '+tr.requires+'. Marshal, the approach controller, ACLS and '+
      'the LSO are module features — without them there is no Case III '+
      'sequence to fly.</p>':'')+
    '<p class="dprem" style="font-size:13px">'+(tr.blurb||[]).join(' ')+'</p>'+
    '<div id="twiz"></div>'+
    '<div class="sechead" style="margin-top:14px">Fly them in order</div>'+
    tr.rides.map(r=>
      '<div class="evrow"><span class="evn">'+String(r.n).padStart(2,'0')+'</span>'+
      '<span class="evt">'+r.label+'<small>'+(r.premise||'')+'</small></span>'+
      (r.graded?'<span class="lchip" style="font-size:10px">graded</span>':
                '<span class="lchip" style="font-size:10px">not graded</span>')+
      '<a href="#" onclick="openDetail(\''+r.key+'\');return false;">open</a></div>').join('')+
    '<div class="dnote">The zip contains every ride as a .miz, a printed brief for '+
    'each, and a syllabus guide generated for the aircraft and tanker you picked above. '+
    'Unzip into Saved Games\\DCS\\Missions and fly 00 first. Each ride also '+
    'generates on its own from the rows above.</div>';
  renderTrackWizard();
  document.getElementById('libdetail').classList.add('on');
  modalOpen(document.getElementById('libdetail'));
  syncGenerationButtons();
}
let trackState=null;
function trackPick(pk,st){ return ((pk[st.era]||{})[st.ac])||[]; }
// Each step re-derives the ones after it from the server's own compatibility
// tree, so a selection that cannot build is never reachable. The rules live in
// missiongen/tracks.py; the browser only renders them.
function setTrack(field,val){
  const tr=OPT.tracks[trackState.id], pk=tr.picker||{};
  trackState[field]=val;
  if(field==='era'||!(pk[trackState.era]||{})[trackState.ac])
    trackState.ac=Object.keys(pk[trackState.era]||{})[0];
  const tks=trackPick(pk,trackState);
  if(!tks.includes(trackState.tk)) trackState.tk=tks[0];
  renderTrackWizard();
}
function trackQuery(){ const s=trackState;
  if(!(OPT.tracks[s.id]||{}).configurable) return '';     // nothing to pick, nothing to send
  return '?era='+encodeURIComponent(s.era)+'&aircraft='+encodeURIComponent(s.ac)+
         '&tanker='+encodeURIComponent(s.tk); }
function renderTrackWizard(){
  const tr=OPT.tracks[trackState.id], pk=tr.picker||{}, s=trackState;
  const row=(label,hint,items,cur,field)=>
    '<div class="dblock"><h4>'+label+' <span style="font-weight:400;color:var(--dim)">'+hint+'</span></h4>'+
    '<div class="pillrow">'+items.map(i=>
      '<button class="pbtn '+(i.k===cur?'on':'')+'" onclick="setTrack(\''+field+'\',\''+i.k+'\')">'+
      i.l+'</button>').join('')+'</div></div>';
  const eras=Object.keys(pk).map(k=>({k,l:(OPT.eras[k]||{}).label||k}));
  const acs=Object.keys(pk[s.era]||{}).map(k=>({k,l:acLabel(k)||k}));
  const tks=trackPick(pk,s).map(k=>({k,l:tankerLabel(k)}));
  // Tankers this lane could use but not in this era, with the reason. A picker
  // that silently omits the KA-6D from the modern era reads as a missing
  // feature; naming the absence turns it into the history lesson it is.
  const gone=((tr.excluded||{})[s.era]||[]);
  // A tanker that IS offered but did not serve through the whole era gets a
  // label, not an omission — the KA-6D retired in 1997 and the modern bucket
  // starts in 2000, and hiding it costs a real DCS asset for the sake of a
  // bucket boundary.
  const pn=((tr.period_notes||{})[s.era]||{})[s.tk];
  const goneRow =
    (pn?'<div class="dnote" style="margin-top:-4px"><b>'+tankerLabel(s.tk)+
        '</b> — '+pn+'</div>':'')+
    (gone.length
      ? '<div class="dnote" style="margin-top:-4px">'+gone.map(g=>
          '<div><b>'+tankerLabel(g[0])+'</b> — '+g[1]+'</div>').join('')+'</div>'
      : '');
  // A track pinned to one airframe (White Knights, Case III, Timing) has no
  // series to build: the summary says `configurable: false`. Rendering the
  // wizard anyway drew three empty rows and "undefined behind a undefined".
  const fixed=!tr.configurable;
  document.getElementById('twiz').innerHTML=
    (fixed ? '' :
    '<div class="sechead" style="margin-top:4px">Build your series</div>'+
    row('Era','— which tankers and jets existed',eras,s.era,'era')+
    row('Your aircraft','— only airframes that can actually take fuel this way',acs,s.ac,'ac')+
    row('Tanker','— only tankers that will fuel it in this era',tks,s.tk,'tk')+
    goneRow)+
    '<div class="dcta">'+
      // THE WHOLE-SYLLABUS BUTTON ONLY EXISTS WHEN A PACK DOES.
      //
      // It used to build eleven missions inside the request, which took the
      // server down. The build is gone, so the button is only honest when the
      // syllabus has actually been published as a pack — otherwise the rides
      // are flown one at a time, which is a single mission per request and has
      // never been a problem.
      (tr.published
        ? '<a class="prime" style="text-decoration:none;text-align:center" href="/api/track/'+
          trackState.id+'/all.zip" download><svg class="icon"><use href="#i-download"/></svg> '+
          'Download all '+tr.rides.length+' missions (.zip)</a>'
        : '')+
      (tr.guide?'<a class="ghost" style="text-decoration:none;text-align:center" href="/api/track/'+
        trackState.id+'/guide.pdf'+trackQuery()+'" download><svg class="icon"><use href="#i-book"/></svg> '+
        'Printed syllabus guide</a>':'')+
    '</div>'+
    (tr.published ? '' :
      '<div class="dnote" style="margin-top:8px;border-left:3px solid var(--accent);'+
      'padding-left:10px">This syllabus is not published as a pack on this '+
      'server, so there is no one-click bundle. <b>Generate each ride from the '+
      'rows below</b> — they are the same missions, one at a time.</div>')+
    (fixed
      ? '<div class="dnote" style="margin-top:8px">Flown in the <b>'+(acLabel(tr.aircraft)||tr.aircraft)+
        '</b>, '+((OPT.eras[(tr.eras||[])[0]]||{}).label||'')+'. Every brief and kneeboard is generated for it.</div>'
      : '<div class="dnote" style="margin-top:8px">Your series: <b>'+(acLabel(s.ac)||s.ac)+
        '</b> behind a <b>'+tankerLabel(s.tk)+'</b>, '+((OPT.eras[s.era]||{}).label||s.era)+
        '. Every brief, every kneeboard and the printed guide are generated for that combination.</div>');
}

// WHAT YOU MUST OWN, ABOVE THE DOWNLOAD BUTTON AND NOT BELOW IT.
// A pack is finished missions on a fixed terrain in a fixed airplane. Telling
// somebody afterwards that he needed Sinai is the say/do gap wearing a
// shopping receipt, so `requires` from the pack manifest is rendered before
// the thing that starts the download.
function packRequires(p){
  const r = (p && p.requires) || {};
  const terr = (r.terrain_names && r.terrain_names.length ? r.terrain_names
                : (r.terrains||[]));
  const mods = r.modules || [];
  if(!terr.length && !mods.length) return '';
  const bits = [];
  if(terr.length) bits.push('<b>'+terr.join('</b>, <b>')+'</b>');
  if(mods.length) bits.push('<b>'+mods.join('</b>, <b>')+'</b>');
  return '<div class="dnote" style="border-left:3px solid var(--accent);'+
         'padding-left:10px;margin-bottom:10px">To fly this you need '+
         bits.join(' and ')+'.</div>';
}
function numWord(n){
  const w = ['','one mission','two missions','three missions','four missions',
             'five missions','six missions','seven missions','eight missions',
             'nine missions','ten missions','eleven missions','twelve missions'];
  return w[n] || (n+' missions');
}
function tankerLabel(k){ const t=(OPT.tankers||{})[k]; return t?t.label:k; }
function openDetail(k, pref){
  if(k.startsWith('track_')) return openTrack(k.slice(6), pref);
  const t=libFind(k); if(!t) return;
  ga('library_open', {mission: k});
  libState.cur=k; libState.era=(pref&&pref.era&&(t.eras||[]).includes(pref.era))?pref.era:t.eras[0];
  libState.crew='qualified'; libState.seed=1000+Math.floor(Math.random()*8999);
  libState.aircraft=acDefaultFor(t, libState.era);
  // The pipeline opens a card with the jet the course is built for, when the
  // card offers it. A card that does not offer it keeps its own default —
  // never a key the engine would reject.
  if(pref&&pref.aircraft&&acChoices(t, libState.era).includes(pref.aircraft)) libState.aircraft=pref.aircraft;
  const r=ROLES[t.role]||ROLES.training, req=libReq(t);
  const eras=(t.eras||[]).length>1
    ? t.eras.map(e=>'<button class="pbtn '+(e===libState.era?'on':'')+'" onclick="pickEra(\''+e+'\')">'+(OPT.eras[e]?.label||e)+'</button>').join('')
    : '<button class="pbtn on" style="cursor:default">'+eraLabels(t.eras)+'</button>';
  const crew=t.aircraft_locked
    ? '<div class="dblock"><h4>Crew difficulty</h4><div class="pillrow">'+
      ['qualified','trainee'].map(c=>'<button class="pbtn '+(c===libState.crew?'on':'')+'" onclick="pickCrew(\''+c+'\')">'+
      (c==='qualified'?'Qualified — your calls':'Trainee — crew hints')+'</button>').join('')+'</div></div>' : '';
  document.getElementById('dcardinner').innerHTML=
    '<button class="dclose" onclick="closeDetail()">×</button>'+
    '<div class="drole"><div class="ric" style="background:'+r.c+'22">'+roleIcon(r)+'</div>'+
      '<div class="role" style="color:'+r.c+'">'+r.label+'</div></div>'+
    '<h2>'+(t.track?t.label:t.label.split(' —')[0])+'</h2><p class="dprem">'+(t.premise||'')+'</p>'+
    '<div class="lchips" style="margin-bottom:18px">'+
      '<span class="lchip">Aircraft: '+(acChoices(t,libState.era).length
        ? 'your pick — '+acChoices(t,libState.era).length+' types'
        : (t.recipe?.aircraft?prettyAc(t.recipe.aircraft):(t.aircraft_locked?'F-14 (locked)':'your pick')))+'</span>'+
      '<span class="lchip">'+(t.players||'SP')+'</span>'+
      '<span class="lchip">Threat '+thrBar(t.threat||1)+'</span>'+
      (t.needs_carrier?'<span class="lchip"><svg class="icon"><use href="#i-anchor"/></svg> Carrier</span>':'')+
      (req?'<span class="lchip" style="color:#ffd27a">Requires '+req+'</span>':'')+
      // A PAID MODULE, ON THE PANEL A PILOT ACTUALLY OPENS. The chip on the
      // grid card is not enough for these rides: a ride that belongs to a
      // track is never a grid card, so the only surfaces it has are this
      // panel and the track panel. Both say it.
      (t.requires?'<span class="lchip needsmod"><svg class="icon"><use href="#i-lock"/></svg> Requires '+t.requires+'</span>':'')+'</div>'+
    '<div class="dblock"><h4>Era</h4><div class="pillrow" id="dEras">'+eras+'</div></div>'+
    acChoiceBlock(t)+crew+
    '<div class="dblock"><h4>What\'s set up for you</h4><ul class="incl">'+
      inclLines(t).map(x=>'<li><span class="k">✓</span>'+x+'</li>').join('')+'</ul></div>'+
    (t.pack
      // Curated pack (AWI Basics): the syllabus TRAVELS TOGETHER — one card,
      // every event listed in flying order, each with its .miz + printed
      // brief, and one button for the whole thing.
      ? packRequires(t.pack)+
        '<div class="dcta">'+
          '<a class="prime" style="text-decoration:none;text-align:center" '+
            'href="/api/pack/'+t.pack.id+'/all.zip" download><svg class="icon"><use href="#i-download"/></svg> Download complete syllabus (.zip)</a>'+
          (t.pack.guide_pdf ? '<a class="ghost" style="text-decoration:none;text-align:center" '+
            'href="/api/pack/'+t.pack.id+'/'+t.pack.guide_pdf+'" download><svg class="icon"><use href="#i-book"/></svg> In-flight guide</a>' : '')+
          (t.pack.readme_pdf ? '<a class="ghost" style="text-decoration:none;text-align:center" '+
            'href="/api/pack/'+t.pack.id+'/'+t.pack.readme_pdf+'" download><svg class="icon"><use href="#i-file"/></svg> Read me first</a>' : '')+
        '</div>'+
        ((t.pack.events||[]).length
          ? '<div class="sechead" style="margin-top:14px">The '+numWord(t.pack.events.length)+' — fly them in order</div>'+
            t.pack.events.map(ev=>
              '<div class="evrow"><span class="evn">'+String(ev.n).padStart(2,'0')+'</span>'+
              '<span class="evt">'+ev.label.replace(/^AWI \d+ · /,'')+
                '<small>'+(ev.premise||'')+'</small></span>'+
              '<a href="/api/pack/'+t.pack.id+'/'+ev.miz+'" download>.miz</a>'+
              '<a href="/api/pack/'+t.pack.id+'/'+ev.brief_pdf+'" download>brief</a></div>').join('')
          : '')+
        '<div class="dnote">Published pack'+
        (t.pack.version?' v'+t.pack.version:'')+
        (t.pack.size_mb?' · '+t.pack.size_mb+' MB':'')+
        ' — exact missions, byte for byte, not generated when you press the '+
        'button. Unzip into Saved Games\\DCS\\Missions and fly 01 first.</div>'
      : '<div class="dcta"><button class="prime" id="dgen" onclick="generateFromLib(\''+k+'\')"><svg class="icon"><use href="#i-download"/></svg> Generate &amp; Download</button>'+
        '<button class="ghost" onclick="openInBuilder(\''+k+'\')"><svg class="icon"><use href="#i-sliders"/></svg> Open in Builder to tweak</button></div>'+
        '<p id="libstatus" role="status" aria-live="polite"></p>'+
        '<div id="libkit" class="revlist" style="display:none;margin-top:12px"></div>'+
        '<div class="dnote">Pre-fills every builder step — change anything, keep the rest, then fly.</div>');
  document.getElementById('libdetail').classList.add('on');
  modalOpen(document.getElementById('libdetail'));
  syncGenerationButtons();
}
function prettyAc(key){ const a=(OPT.aircraft||[]).find(x=>x.key===key); return a?a.id:key; }
function closeDetail(){ document.getElementById('libdetail').classList.remove('on'); modalClose(); }
function pickEra(e){ libState.era=e;
  document.querySelectorAll('#dEras .pbtn').forEach(b=>b.classList.toggle('on',b.textContent===(OPT.eras[e]?.label||e)));
  // The offered airframes are era-specific, so switching era has to re-pick
  // AND re-render. Leaving a Spitfire selected under "Modern" would have sent
  // the engine a jet the era guard rejects — the card looking broken when the
  // STATE was stale (the same failure mode by_era was added to fix).
  const t=libFind(libState.cur); if(!t) return;
  libState.aircraft=acDefaultFor(t, e);
  const row=document.getElementById('dAcRow'); if(row) row.innerHTML=acChoiceRow(t);
}
function pickCrew(c){ libState.crew=c; document.querySelectorAll('#libdetail .pbtn').forEach(b=>{ if(b.textContent.startsWith('Qualified')||b.textContent.startsWith('Trainee')) b.classList.toggle('on',(c==='qualified')===b.textContent.startsWith('Qualified')); }); }
function setupFromLib(k){
  const t=OPT.templates[k], era=libState.era||t.eras[0];
  // a WWII card cannot use a default map with no WWII preset
  const map=((t.by_era||{})[era]||{}).map || t.default_map || S.map;
  document.querySelector('#eras .card[data-k="'+era+'"]')?.click();
  const mc=document.querySelector('#maps .card[data-k="'+map+'"]'); if(mc) mc.click();
  applyScenarioPreset(k);
  // The drawer's aircraft pick wins over the card's pin. AFTER the preset,
  // because applyScenarioPreset() calls refreshAircraft() and then sets the
  // pinned jet — setting it earlier would be overwritten.
  if(libState.aircraft && acChoices(t, era).length){
    const a=document.getElementById('aircraft');
    if(a && [...a.options].some(o=>o.value===libState.aircraft)) a.value=libState.aircraft;
  }
  if(t.aircraft_locked){ const cd=document.getElementById('crew_difficulty'); if(cd) cd.value=libState.crew; }
  document.getElementById('seed').value=libState.seed;
  sum(); updateRail();
}
async function generateFromLib(k){
  if(GENERATING) return;
  setupFromLib(k);
  // Capture drawer nodes before awaiting; a newly opened card owns new nodes.
  await generateMission(document.getElementById('dgen'), {source:'library', rc:recipe(),
    box:document.getElementById('libkit'), status:document.getElementById('libstatus')});
}
function openInBuilder(k){ setupFromLib(k); closeDetail(); showView('builder'); showScreen('flight'); }


return { acChoiceBlock, acChoiceRow, acChoices, acDefaultFor, acLabel, acLabelFull, buildRoleTabs, clearFilter, clearFilters, clearModule, closeDetail, closeOwn, eraLabels, esc, filterModule, generateFromLib, inclLines, inferRole, initLibFilters, libCard, libFind, libItems, libPasses, libReq, libSort, libState, mapKeyOf, mapLabel, numWord, openDetail, openInBuilder, openOwn, openReading, openTrack, ownCats, ownClearCat, ownEdit, ownMatch, ownRow, ownSelectAll, ownSetP, ownSet_, ownStore, ownedAc, ownedMaps, pKey, pProgress, pSchoolStats, pSetDone, packRequires, pickAircraft, pickCrew, pickEra, pipeState, prettyAc, renderChips, renderLib, renderModuleRail, renderOwnBody, renderPipeline, renderTrackWizard, reqLabel, rideItem, roleIcon, saveOwn, setRole, setTrack, setupFromLib, tankerLabel, thrBar, toggleOwn, toggleOwnItem, trackOf, trackPick, trackQuery, trackState, unitRow };
}
