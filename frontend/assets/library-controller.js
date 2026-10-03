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
function libItems(){ return Object.entries(OPT.templates)
 .filter(([k,v])=>v&&!k.startsWith('_')&&!v.quick&&!trackOf(k))
 .map(([k,v])=>{const lib=v.library||{},parts=(v.label||k).split(' — ');
  const t={k,...v,role:lib.role||inferRole(k,v),premise:lib.premise||parts[1]||parts[0],
   threat:lib.threat??v.recipe?.threat_intensity??1,players:lib.players||'SP',
   aircraft:v.recipe?.aircraft||null,module:lib.module||null,requires:lib.requires||null,
   kind:v.kind||'open',tasked:!!v.tasked,featured:!!lib.featured};
  t.catalog=buildLibraryCatalog(t,getOptions());return t;
 }); }
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
 if(!ownSetP())return '';
 const req=libReq(t);
 return req?'<div class="ownrow needs">'+(req.unknown?'Compatibility unconfirmed: ':'Needs: ')+esc(reqLabel(req))+'</div>':'<div class="ownrow have">✓ Compatible with your DCS content</div>';
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
 if(libState.initd)return;libState.initd=true;const items=libItems();
 const add=(id,keys,label)=>{const sel=document.getElementById(id);[...new Set(keys)].sort((a,b)=>label(a).localeCompare(label(b))).forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent=label(k);sel.appendChild(o);});};
 add('lfAc',items.flatMap(t=>t.catalog.aircraft),acLabelFull);
 add('lfMap',items.flatMap(t=>t.catalog.maps),mapLabel);
}
function libSort(a,b){
 const sort=document.getElementById('lfSort').value;
 if(sort==='az')return a.catalog.title.localeCompare(b.catalog.title);
 if(sort==='threat')return b.threat-a.threat||a.catalog.title.localeCompare(b.catalog.title);
 return Number(b.featured)-Number(a.featured)||a.catalog.title.localeCompare(b.catalog.title);
}
function filterModule(m){ libState.module=m; renderLib(); window.scrollTo(0,0); }
function renderChips(anyF){
  const bar=document.getElementById('lchipbar'); if(!anyF){ bar.innerHTML=''; return; }
  const chips=[];
  if(libState.module) chips.push(['Module',libState.module,"clearModule()"]);
  if(libState.role!=='all') chips.push(['Role',(ROLES[libState.role]||{}).label||libState.role,"setRole('all')"]);
  const g=id=>document.getElementById(id);
  if(g('lfFormat').value!=='all') chips.push(['Format',g('lfFormat').value==='collection'?'Collections':'Missions',"clearFilter('lfFormat')"]);
  if(g('lfType').value!=='all') chips.push(['Type',g('lfType').options[g('lfType').selectedIndex].text,"clearFilter('lfType')"]);
  if(g('lfAc').value!=='all') chips.push(['Aircraft',acLabel(g('lfAc').value),"clearFilter('lfAc')"]);
  if(g('lfMap').value!=='all') chips.push(['Map',mapLabel(g('lfMap').value),"clearFilter('lfMap')"]);
  if(g('lfEra').value!=='all') chips.push(['Era',g('lfEra').options[g('lfEra').selectedIndex].text,"clearFilter('lfEra')"]);
  if(g('lfDiff').value!=='all') chips.push(['Threat',g('lfDiff').options[g('lfDiff').selectedIndex].text,"clearFilter('lfDiff')"]);
  if(g('lfSearch').value.trim()) chips.push(['Search','“'+g('lfSearch').value.trim()+'”',"clearFilter('lfSearch')"]);
  if(libState.own) chips.push(['','Compatible with my content',"toggleOwn()"]);
  let h=chips.map(([k,v,fn])=>'<button class="fchip" onclick="'+fn+'">'+(k?'<b>'+k+':</b> ':'')+esc(v)+' <span class="x" aria-hidden="true">✕</span></button>').join('');
  if(chips.length) h+='<button class="fclear" onclick="clearFilters()">Clear all</button>';
  bar.innerHTML=h;
}
function clearModule(){ libState.module=null; renderLib(); }
function clearFilter(id){ const e=document.getElementById(id); if(e.type==='search') e.value=''; else e.value='all'; renderLib(); }
function clearFilters(){ libState.role='all'; libState.own=false; libState.module=null;
  document.getElementById('lown').classList.remove('on');document.getElementById('lown').setAttribute('aria-checked','false');
  ['lfType','lfAc','lfMap','lfEra','lfDiff','lfFormat'].forEach(i=>document.getElementById(i).value='all');
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

function libFilters(){const value=id=>document.getElementById(id)?.value;return {era:value('lfEra')==='all'?null:value('lfEra'),map:value('lfMap')==='all'?null:value('lfMap'),aircraft:value('lfAc')==='all'?null:value('lfAc')};}
function ownedModules(){const o=ownStore();return o?.set?new Set(o.modules||[]):null;}
function libCompatibility(t,filters={}){return catalogCompatibility(t.catalog,ownedMaps(),ownedAc(),ownedModules(),filters);}
function libSelection(t,pref){const filters={...libFilters(),...pref};return libCompatibility(t,filters).variant||(pref?libCompatibility(t,pref).variant:null)||libCompatibility(t).variant;}
function setLibraryFormat(value){document.getElementById('lfFormat').value=value;renderLib();}
function detailSummary(t){
 if(t.pack)return '<span class="lchip">Aircraft: '+esc(t.catalog.aircraft.map(acLabel).join(', ')||'See collection requirements')+'</span><span class="lchip">Maps: '+esc(t.catalog.requirements.maps.map(m=>m.label).join(', ')||'Unspecified')+'</span>';
 const n=acChoices(t,libState.era).length;
 return '<span class="lchip">Aircraft: '+esc(acLabel(libState.aircraft)||'Unspecified')+(n>1?' · '+n+' types available':'')+'</span><span class="lchip">Map: '+esc(mapLabel(libState.map))+'</span>';
}
function refreshDetailSummary(t){const box=document.getElementById('dSummary');if(box)box.innerHTML=detailSummary(t)+'<span class="lchip">'+esc(t.players||'SP')+'</span><span class="lchip">'+thrBar(t.threat||1)+'</span>';}
function detailMapRow(t){const keys=[...new Set(t.catalog.variants.filter(v=>v.era===libState.era).map(v=>v.map))];return keys.length>1?'<div class="dblock"><label for="dMap">Map</label><select id="dMap" onchange="pickMap(this.value)">'+keys.map(k=>'<option value="'+k+'"'+(k===libState.map?' selected':'')+'>'+esc(mapLabel(k))+'</option>').join('')+'</select></div>':'';}
function pickMap(key){const t=libFind(libState.cur);if(!t)return;libState.map=key;const choices=acChoices(t,libState.era);if(!choices.includes(libState.aircraft))libState.aircraft=acDefaultFor(t,libState.era);const row=document.getElementById('dAcRow');if(row)row.innerHTML=acChoiceRow(t);refreshDetailSummary(t);document.getElementById('dHistorical').innerHTML=historicalBlock(t,libState.era);}

function libReq(t){
 if(!ownSetP())return null;
 const result=libCompatibility(t);
 return result.compatible?null:{missing:result.missing,unknown:result.unknown};
}
function reqLabel(req){ return (req.missing||[req.ac,req.map]).filter(Boolean).map(x=>acLabel(x)||x).join(' · '); }
function thrBar(n){ const names=['','Minimal','Low','Moderate','High','Maximum'];let s='<span class="thr" aria-hidden="true">';for(let i=1;i<=5;i++)s+='<i class="'+(i<=n?'f'+n:'')+'"></i>';return '<span>Threat: '+(names[n]||n)+' '+s+'</span>'; }
function eraLabels(er){ return (er||[]).map(e=>OPT.eras[e]?OPT.eras[e].label:e).join(' · '); }

function buildRoleTabs(){
 const present=new Set(libItems().flatMap(t=>t.catalog.activity)),order=['a2a','strike','sead','cas','carrier','training','historic'];
 let h='<button class="rtab '+(libState.role==='all'?'on':'')+'" aria-pressed="'+(libState.role==='all')+'" onclick="setRole(\'all\')">All activities</button>';
 for(const k of order)if(present.has(k))h+='<button class="rtab '+(libState.role===k?'on':'')+'" aria-pressed="'+(libState.role===k)+'" onclick="setRole(\''+k+'\')"><span class="rc" style="background:'+ROLES[k].c+'"></span>'+ROLES[k].label+'</button>';
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
    {kind:'modules',id:'additional',title:'Additional modules',items:[{key:'Supercarrier',label:'DCS: Supercarrier'}]},
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
  ownEdit={maps:new Set((o&&o.maps)||[]), aircraft:new Set((o&&o.aircraft)||[]),modules:new Set((o&&o.modules)||[])};
  const h='<button class="dclose" aria-label="Close my DCS content" onclick="closeOwn()">×</button>'+
    '<div class="eyebrow" style="margin-bottom:6px">My DCS install</div>'+
    '<h2 style="margin:0 0 4px;font-size:24px">What do you own?</h2>'+
    '<p class="dprem" style="font-size:13.5px">Tick your terrains, aircraft and additional modules — search by name or nickname (Hornet, Warthog, Fulda…), or Select all per category. Saved on this device only; free content is always included.</p>'+
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
  if(fc) fc.textContent=(ownEdit.maps.size+ownEdit.aircraft.size+ownEdit.modules.size)+' modules marked owned';
}
function saveOwn(){ ownSet_({set:true, maps:[...ownEdit.maps], aircraft:[...ownEdit.aircraft],modules:[...ownEdit.modules]});
  libState.own=true; document.getElementById('lown').classList.add('on');document.getElementById('lown').setAttribute('aria-checked','true'); closeOwn(); renderLib(); }
function ownSet_(o){ try{localStorage.setItem('ms_owned',JSON.stringify(o))}catch(e){} }
function libCard(t){
 const c=t.catalog,r=ROLES[t.role]||ROLES.training;
 const aircraft=c.aircraft.length===1?acLabel(c.aircraft[0]):(t.pack?c.aircraft.map(acLabel).join(', '):'Aircraft selectable');
 const maps=t.pack?c.requirements.maps.map(m=>m.label).join(', '):(c.maps.length===1?mapLabel(c.maps[0]):'Map selectable');
 return '<div class="libcard" role="button" tabindex="0" aria-label="View '+esc(c.title)+'" onclick="openDetail(\''+t.k+'\')">'+
  '<div class="bar" style="background:'+r.c+'"></div><div class="cbody"><div class="rt"><div class="role" style="color:'+r.c+'">'+r.label+'</div><span class="kindb '+(t.kind==='full'?'full':'open')+'">'+c.subtype+(t.pack?' · '+c.count+' missions':'')+'</span></div>'+
  '<h3>'+esc(c.title)+'</h3><p class="prem">'+esc(t.premise||'')+'</p><p class="lsuit">'+esc(aircraft||'Aircraft requirements unconfirmed')+' · '+esc(maps||'Terrain requirements unconfirmed')+'</p>'+
  '<div class="lchips"><span class="lchip">'+esc(eraLabels(t.eras))+'</span><span class="lchip">'+thrBar(t.threat||1)+'</span><span class="lchip">'+esc(t.players||'SP')+'</span></div>'+ownRow(t)+
  (c.requirements.extras.length?'<div class="dnote">Requires '+esc(c.requirements.extras.map(k=>k==='Supercarrier'?'DCS: Supercarrier':k).join(', '))+'</div>':'')+
  '<div class="lview">View '+(t.pack?'collection':'mission')+' →</div></div></div>';
}
function libPasses(t){
 const c=t.catalog,g=id=>document.getElementById(id).value;
 if(libState.module&&t.module!==libState.module)return false;
 if(libState.role!=='all'&&!c.activity.includes(libState.role))return false;
 if(g('lfFormat')!=='all'&&c.structure!==g('lfFormat'))return false;
 if(g('lfType')!=='all'&&(t.pack||t.kind!==g('lfType')))return false;
 const filters=libFilters();
 if(filters.era&&!(t.eras||[]).includes(filters.era))return false;
 if(filters.aircraft&&!c.aircraft.includes(filters.aircraft))return false;
 if(filters.map&&!c.maps.includes(filters.map))return false;
 if(!t.pack&&!c.variants.some(v=>(!filters.era||v.era===filters.era)&&(!filters.aircraft||v.aircraft===filters.aircraft)&&(!filters.map||v.map===filters.map)))return false;
 const d=g('lfDiff'),th=t.threat||1;if(d==='lo'&&th>2||d==='md'&&th!==3||d==='hi'&&th<4)return false;
 const q=g('lfSearch').trim().toLowerCase();
 if(q){const hay=[c.title,t.premise,t.module,...c.aircraft.flatMap(k=>[acLabelFull(k),k,OWN_ALIAS[k]]),...c.maps.flatMap(k=>[mapLabel(k),OWN_ALIAS[k]]),...c.activity.map(k=>ROLES[k]?.label||k),...(t.pack?.events||[]).map(e=>e.label)].join(' ').toLowerCase();if(!hay.includes(q))return false;}
 return !libState.own||libCompatibility(t,filters).compatible;
}
function renderLib(){
 initLibFilters();const items=libItems(),g=id=>document.getElementById(id);
 const anyF=libState.module||libState.role!=='all'||['lfEra','lfDiff','lfType','lfAc','lfMap','lfFormat'].some(id=>g(id).value!=='all')||g('lfSearch').value.trim()||libState.own;
 const list=items.filter(libPasses).sort(libSort),featured=anyF?[]:list.filter(t=>t.featured).slice(0,3),keys=new Set(featured.map(t=>t.k));
 g('lfeatwrap').style.display=featured.length?'':'none';g('lfeat').innerHTML=featured.map(libCard).join('');
 g('lallhead').textContent=anyF?'Results':featured.length?'More to fly':'All content';
 g('lgrid').innerHTML=list.length?list.filter(t=>!keys.has(t.k)).map(libCard).join(''):'<div class="lempty">No content matches these filters.<div class="dcta"><button class="ghost" onclick="clearFilters()">Clear filters</button><button class="prime" onclick="showView(\'builder\')">Open Builder</button></div></div>';
 g('libcount').textContent=list.length+' items · '+list.filter(t=>!t.pack).length+' missions · '+list.filter(t=>t.pack).length+' collections';
 document.querySelectorAll('[data-lib-format]').forEach(b=>{const on=b.dataset.libFormat===g('lfFormat').value;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));});renderChips(anyF);
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
function acChoices(t, era){ return t.pack?[]:[...new Set(t.catalog.variants.filter(v=>v.era===era&&(!libState.map||v.map===libState.map)).map(v=>v.aircraft))]; }
function acDefaultFor(t, era){const choices=acChoices(t,era),pin=t.by_map?.[libState.map]?.aircraft||t.by_era?.[era]?.aircraft||t.recipe?.aircraft;return choices.includes(pin)?pin:choices[0]||null;}
function acChoiceRow(t){
  const era=libState.era, list=acChoices(t, era);
  if(!list.length) return '';
  // Only offer aircraft the roster actually knows about, so a data typo drops
  // one button instead of handing the engine an unbuildable key.
  const known=list.filter(key=>(OPT.aircraft||[]).some(a=>a.key===key));
  if(!known.length) return '';
  return known.map(key=>'<button class="pbtn '+(key===libState.aircraft?'on':'')+
    '" aria-pressed="'+(key===libState.aircraft)+'" onclick="pickAircraft(\''+key+'\')">'+(acLabel(key)||key)+'</button>').join('');
}
function acChoiceBlock(t){
  if(!acChoices(t, libState.era).length) return '';
  return '<div class="dblock"><h4>Aircraft</h4>'+
    '<div class="pillrow" id="dAcRow">'+acChoiceRow(t)+'</div></div>';
}
function pickAircraft(key){
  libState.aircraft=key;
  const t=libFind(libState.cur); if(!t) return;
  const row=document.getElementById('dAcRow'); if(row) row.innerHTML=acChoiceRow(t);refreshDetailSummary(t);
}
function libFind(k){ const t=libItems().find(x=>x.k===k)||rideItem(k);if(t&&!t.catalog)t.catalog=buildLibraryCatalog(t,getOptions());return t; }
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
    '<button class="dclose" aria-label="Close details" onclick="closeDetail()">×</button>'+
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
    '<button class="dclose" aria-label="Close details" onclick="closeDetail()">×</button>'+
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
function packHref(id,name){return '/api/pack/'+encodeURIComponent(id)+'/'+String(name).split('/').map(encodeURIComponent).join('/');}
function packRequires(p){
  const r = (p && p.requires) || {};
  const terr = (r.terrain_names && r.terrain_names.length ? r.terrain_names
                : (r.terrains||[]));
  const mods = r.modules || [];
  if(!terr.length && !mods.length) return '';
  const bits = [];
  if(terr.length) bits.push('<b>'+terr.map(esc).join('</b>, <b>')+'</b>');
  if(mods.length) bits.push('<b>'+mods.map(esc).join('</b>, <b>')+'</b>');
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
function historicalBlock(t, era){
  const map=libState.map||((t.by_era||{})[era]||{}).map || t.default_map || S.map;
  const h=((t.historical_context||{})[era]||{})[map];
  if(!h) return t.pack ? '<p class="dnote">Historical context is not supplied for this published pack. Consult its author’s brief.</p>' : '';
  return '<div class="dblock"><h4>Historical context</h4><p>'+esc(h.date)+' · '+esc(h.label)+'</p>'+
    '<details class="libhistory"><summary>Setting, sources &amp; adaptations</summary><ul>'+ (h.notes||[]).map(n=>'<li>'+esc(n)+'</li>').join('')+'</ul>'+
    '<p class="dnote">Recorded weapon service years are checked; unknown dates, operators and module variants remain uncertified.</p>'+
    (h.sources||[]).filter(u=>/^https:\/\//.test(u)).map((u,i)=>'<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">Source '+(i+1)+'</a> ').join('')+'</details></div>';
}
function openDetail(k, pref){
 if(k.startsWith('track_')) return openTrack(k.slice(6), pref);
 const t=libFind(k);if(!t)return;const c=t.catalog;
 ga('library_open',{mission:k});libState.cur=k;libState.crew='qualified';libState.seed=1000+Math.floor(Math.random()*8999);
 const selected=libSelection(t,pref);libState.era=selected?.era||(t.eras||[])[0];libState.map=selected?.map||t.default_map;libState.aircraft=selected?.aircraft||acDefaultFor(t,libState.era);
 if(pref&&pref.aircraft&&acChoices(t, libState.era).includes(pref.aircraft))libState.aircraft=pref.aircraft;
 const req=libReq(t),eras=[...new Set(c.variants.map(v=>v.era))];
 const choices=!t.pack?'<div class="dblock"><h4>Era</h4><div class="pillrow" id="dEras">'+eras.map(e=>'<button class="pbtn '+(e===libState.era?'on':'')+'" data-era="'+e+'" aria-pressed="'+(e===libState.era)+'" onclick="pickEra(\''+e+'\')">'+esc(OPT.eras[e]?.label||e)+'</button>').join('')+'</div></div><div id="dMaps">'+detailMapRow(t)+'</div>'+acChoiceBlock(t):'';
 const crew=t.aircraft_locked?'<div class="dblock"><h4>Crew difficulty</h4><div class="pillrow">'+['qualified','trainee'].map(v=>'<button class="pbtn '+(v===libState.crew?'on':'')+'" onclick="pickCrew(\''+v+'\')">'+(v==='qualified'?'Qualified — your calls':'Trainee — crew hints')+'</button>').join('')+'</div></div>':'';
 const actions=t.pack?packRequires(t.pack)+'<div class="dcta"><a class="prime" href="/api/pack/'+t.pack.id+'/all.zip" download><svg class="icon"><use href="#i-download"/></svg> Download collection · '+c.count+' missions</a>'+(t.pack.guide_pdf?'<a class="ghost" href="'+packHref(t.pack.id,t.pack.guide_pdf)+'" download>In-flight guide</a>':'')+(t.pack.readme_pdf?'<a class="ghost" href="'+packHref(t.pack.id,t.pack.readme_pdf)+'" download>Read me first</a>':'')+'</div>':
  '<div class="dcta"><button class="prime" id="dgen" onclick="generateFromLib(\''+k+'\')"><svg class="icon"><use href="#i-download"/></svg> Generate &amp; Download</button><button class="ghost" onclick="openInBuilder(\''+k+'\')">Customize in Builder</button></div><p id="libstatus" role="status" aria-live="polite"></p><div id="libkit" class="revlist" style="display:none;margin-top:12px"></div>';
 const events=t.pack?'<div class="sechead">'+c.count+' missions — fly them in order</div>'+(t.pack.events||[]).map(ev=>'<div class="evrow"><span class="evn">'+String(ev.n).padStart(2,'0')+'</span><span class="evt">'+esc(ev.label)+'<small>'+esc(ev.premise||'')+'</small></span><div class="evlinks"><a href="'+packHref(t.pack.id,ev.miz)+'" aria-label="Download mission '+esc(ev.label)+'" download>Mission</a>'+(ev.brief_pdf?'<a href="'+packHref(t.pack.id,ev.brief_pdf)+'" aria-label="Download briefing '+esc(ev.label)+'" download>Briefing</a>':'')+'</div></div>').join('')+'<div class="dnote">Published collection'+(t.pack.version?' v'+esc(t.pack.version):'')+(t.pack.size_mb?' · '+t.pack.size_mb+' MB':'')+'. These are stored missions. Unzip into Saved Games\\DCS\\Missions and follow the sequence above.</div>':
  '<div class="dblock"><h4>What\'s set up for you</h4><ul class="incl">'+inclLines(t).map(x=>'<li><span class="k">✓</span>'+x+'</li>').join('')+'</ul></div><p class="dnote">Selections fill the Builder. Customize any setting before you fly.</p>';
 document.getElementById('dcardinner').innerHTML='<div class="detailhead"><span>'+c.subtype+(t.pack?' · '+c.count+' missions':'')+'</span><button class="dclose" aria-label="Close details" onclick="closeDetail()">×</button></div>'+
  '<h2>'+esc(c.title)+'</h2>'+(t.premise?.length>220?'<details class="libhistory"><summary>About this collection</summary><p class="dprem">'+esc(t.premise)+'</p></details>':'<p class="dprem">'+esc(t.premise||'')+'</p>')+
  '<div class="lchips" id="dSummary"></div>'+(req?'<div class="ownrow needs">'+(req.unknown?'Compatibility unconfirmed: ':'Needs: ')+esc(reqLabel(req))+'</div>':'')+
  (c.requirements.extras.length?'<div class="ownrow needs">Requires '+esc(c.requirements.extras.map(k=>k==='Supercarrier'?'DCS: Supercarrier':k).join(', '))+'</div>':'')+
  choices+crew+actions+events+'<div id="dHistorical">'+historicalBlock(t,libState.era)+'</div>';
 refreshDetailSummary(t);document.getElementById('dcardinner').scrollTop=0;
 document.getElementById('libdetail').classList.add('on');modalOpen(document.getElementById('libdetail'));syncGenerationButtons();
}
function prettyAc(key){ const a=(OPT.aircraft||[]).find(x=>x.key===key); return a?a.id:key; }
function closeDetail(){ document.getElementById('libdetail').classList.remove('on'); modalClose(); }
function pickEra(e){
 const t=libFind(libState.cur);if(!t||t.pack)return;
 libState.era=e;const match=libCompatibility(t,{era:e}).variant;libState.map=match?.map||t.default_map;libState.aircraft=acDefaultFor(t,e);
 document.querySelectorAll('#dEras .pbtn').forEach(b=>{const on=b.dataset.era===e;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));});
 const row=document.getElementById('dAcRow');if(row)row.innerHTML=acChoiceRow(t);
 document.getElementById('dMaps').innerHTML=detailMapRow(t);refreshDetailSummary(t);
 document.getElementById('dHistorical').innerHTML=historicalBlock(t,e);
}
function pickCrew(c){ libState.crew=c; document.querySelectorAll('#libdetail .pbtn').forEach(b=>{ if(b.textContent.startsWith('Qualified')||b.textContent.startsWith('Trainee')) b.classList.toggle('on',(c==='qualified')===b.textContent.startsWith('Qualified')); }); }
function setupFromLib(k){
  const t=libFind(k), era=libState.era||t.eras[0];
  // a WWII card cannot use a default map with no WWII preset
  const map=libState.map||((t.by_era||{})[era]||{}).map || t.default_map || S.map;
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


return { setLibraryFormat, pickMap, libCompatibility, libSelection, ownedModules, detailSummary, acChoiceBlock, acChoiceRow, acChoices, acDefaultFor, acLabel, acLabelFull, buildRoleTabs, clearFilter, clearFilters, clearModule, closeDetail, closeOwn, eraLabels, esc, filterModule, generateFromLib, inclLines, inferRole, initLibFilters, libCard, libFind, libItems, libPasses, libReq, libSort, libState, mapKeyOf, mapLabel, numWord, openDetail, openInBuilder, openOwn, openReading, openTrack, ownCats, ownClearCat, ownEdit, ownMatch, ownRow, ownSelectAll, ownSetP, ownSet_, ownStore, ownedAc, ownedMaps, pKey, pProgress, pSchoolStats, pSetDone, packRequires, pickAircraft, pickCrew, pickEra, pipeState, prettyAc, renderChips, renderLib, renderOwnBody, renderPipeline, renderTrackWizard, reqLabel, rideItem, roleIcon, saveOwn, setRole, setTrack, setupFromLib, tankerLabel, thrBar, toggleOwn, toggleOwnItem, trackOf, trackPick, trackQuery, trackState, unitRow };
}
