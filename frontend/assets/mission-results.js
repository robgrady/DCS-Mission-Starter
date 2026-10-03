/** Result-owned downloads and admission state, with explicit UI/network adapters. */
function createMissionResults({getOptions, callbacks, environment}) {
const {document, fetch, URL} = environment;
const {esc, recipe, visitorId, ga, showScreen, qfEra, QF, ALL_STEP_IDS} = callbacks;
const OPT = new Proxy({}, {get: (_, key) => getOptions()?.[key]});
// Generation lifecycle and result-owned artifact downloads.
// Classic script boundary preserves existing inline UI entry points.
let LAST_GEN_RECIPE = null;   // last successful generation, for contact context only
let GENERATING = false;
const MISSION_RESULTS = {builder:null, quick:null, library:null};

// Mission Kits own an immutable snapshot of the successful recipe. Every
// document button closes over that result, including when several Kits exist.
function kitRows(kit, fname, warn, rc){
  // rc = the recipe that was actually generated. Quick Flight builds recipes
  // off-DOM, so the kit can't read builder inputs; the builder passes its own.
  rc = rc || {};
  const n = rc.slots || 1;
  const rows = [];
  const row = (ico, title, sub, right) =>
    rows.push('<div class="kitrow"><span class="kitico">'
      +'<svg class="icon"><use href="#i-'+ico+'"/></svg></span>'+
      '<div class="kitbody"><b>'+title+'</b><small>'+sub+'</small></div>'+(right||'')+'</div>');
  row('archive', esc(fname),
    n > 1 ? 'Multiplayer — '+n+' client seats. Host it: Multiplayer → New Server, or drop it on your dedicated server. No single-player slot.'
          : 'Single-player. Install path: <span class="kitpath">Saved Games\\DCS\\Missions</span> — then Mission → fly.',
    '<span class="kitok">DOWNLOAD STARTED ✓</span>');
  row('file', 'Briefing pack — PDF + Markdown',
    'The full mission brief as documents: situation, comms &amp; TACAN card, threat picture. Print it or second-screen it.',
    '<button class="kitbtn kit_brief">Download</button>');
  if (kit.kneeboard_pages)
    row('clipboard', 'Kneeboard — '+kit.kneeboard_pages+' pages, already in the jet',
      'In the cockpit: RShift+K, [ ] to flip pages. Download them as PNGs to use '
      + 'in OpenKneeboard, print them, or send them to your flight.',
      '<span class="kitok">IN THE .MIZ ✓</span> <button class="kitbtn kit_kb">Download PNGs</button>');
  if (kit.dtc)
    row('save', 'DTC setup card', 'Data cartridge reference for the F-14B(U) — nav points, threats and comms preloaded.',
      '<span class="kitok">IN THE .MIZ ✓</span>');
  if (kit.route)
    row('compass', 'Flight plan loaded', esc(kit.route) + ' — fly the black line, hit your TOT.',
      '<span class="kitok">IN THE .MIZ ✓</span>');
  // YOUR loadout, before anything about the enemy: it is the one thing on this
  // panel the user can act on before they press fly.
  if (kit.player_loadout){
    const ROLEW = {cap:'air-to-air', strike:'strike', cas:'close air support',
                   sead:'SEAD', training:'training', bfm:'the merge',
                   antiship:'anti-ship'};
    row('medal', 'Your loadout — ' + (ROLEW[kit.player_role] || 'mission') + ' fit',
      '<b>' + esc(kit.player_loadout) + '</b>. Chosen from the mission type and checked '
      + 'against what DCS allows on each station. Change it in the Mission Editor '
      + 'any time.',
      '<span class="kitok">ON YOUR JET ✓</span>');
  }
  // Enemy air: the FIT, not just the type. Knowing he only has rear-quarter
  // IR changes how you fly the merge — that belongs in front of the user
  // before they open a document, not only inside one.
  const ea = kit.enemy_air || [];
  const merge = ea.find(a => a.r === 'merge');
  if (kit.bfm)
    row('swords', esc(kit.bfm.replace('Bandit BFM','Your adversary')),
      (merge ? 'Carrying <b>'+esc(merge.fit)+'</b>. '+esc(merge.imp)+' ' : '')
      + esc(kit.bfm_geometry || '') + ' Re-roll (the dice) for a different type on the same picks.',
      '<span class="kitok">AT THE MERGE ✓</span>');
  ea.filter(a => a.r !== 'merge').forEach(a =>
    row('target', 'Enemy air — '+esc(a.n)+'× '+esc(a.t),
      'Carrying <b>'+esc(a.fit)+'</b>. '+esc(a.imp),
      '<span class="kitok">ARMED ✓</span>'));
  if (kit.support && kit.support.length)
    row('radar', 'Support placed: '+kit.support.map(esc).join(' · '),
      'See the comms card in the briefing and kneeboard for applicable frequencies and TACAN.');
  if (warn)
    row('warn', 'Generated with warnings', esc(warn));
  return rows.join('');
}

function wireKitButtons(box, result){
  const brief = box.querySelector('.kit_brief');
  if (brief) brief.onclick = ()=>downloadBrief(brief, result);
  const kb = box.querySelector('.kit_kb');
  if (kb) kb.onclick = ()=>downloadKneeboard(kb, result);
}

function showKit(result, box){
  if (!box) return;
  box.innerHTML = kitRows(result.kit, result.fname, result.warn, result.rc)
    + '<p class="kitstatus" role="status" aria-live="polite"></p>';
  box.style.display = '';
  wireKitButtons(box, result);
  if (result.source === 'builder'){
    ALL_STEP_IDS.forEach(id=>{ const step=document.getElementById(id); if(step) step.style.display='none'; });
    const cols=document.getElementById('stepcols'); if(cols) cols.style.display='none';
    document.getElementById('sec_kit').style.display = '';
    document.getElementById('screennav').style.display = 'none';
  }
  // A Library drawer may have closed or been replaced while the request ran.
  if (box.isConnected && box.offsetParent !== null){
    box.setAttribute('tabindex','-1'); box.focus({preventScroll:true});
    box.scrollIntoView({behavior:'smooth', block:'start'});
  }
}
function closeKit(){
  document.getElementById('sec_kit').style.display = 'none';
  document.getElementById('screennav').style.display = '';
  showScreen('review');
}
function freezeRecipe(value){
  const snapshot = JSON.parse(JSON.stringify(value));
  function freeze(v){
    if (v && typeof v==='object'){ Object.values(v).forEach(freeze); Object.freeze(v); }
    return v;
  }
  return freeze(snapshot);
}
function syncGenerationButtons(){
  for (const id of ['gen2','dgen']){
    const btn=document.getElementById(id); if(btn) btn.disabled=GENERATING;
  }
  const fly=document.getElementById('qf_fly');
  if(fly) fly.disabled = GENERATING || !OPT || !qfEra(QF.type,QF.map,QF.ac);
}
async function responseError(res){
  // Proxies and interrupted deployments can return HTML instead of API JSON.
  try { const data=await res.json(); return typeof data.detail==='string' ? data.detail : JSON.stringify(data.detail||data); }
  catch(e){ return 'Request failed ('+res.status+'). Please try again.'; }
}
function saveDownload(blob, fname){
  const a=document.createElement('a'), url=URL.createObjectURL(blob);
  a.href=url; a.download=fname; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),60000);
}
async function generateMission(btn, options={}){
  if (GENERATING) return null;
  const source=options.source||'builder';
  const rc=freezeRecipe(options.rc||recipe());
  const box=options.box||document.getElementById({builder:'kit_box',quick:'qfkit',library:'libkit'}[source]);
  const statuses=options.status ? [options.status] : source==='quick'
    ? [document.getElementById('qf_hint')]
    : [document.getElementById('status'),document.getElementById('status2')];
  const status=text=>statuses.forEach(node=>{if(node) node.textContent=text;});
  const oldLabel=btn ? btn.innerHTML : '';
  GENERATING=true; syncGenerationButtons();
  if(btn) btn.textContent='Generating…';
  status('Generating…');
  try{
    const res=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({recipe:rc,source,visitor:visitorId()})});
    if(!res.ok){ ga('generate_error',{source}); status('Error: '+await responseError(res)); return null; }
    const blob=await res.blob();
    let kit={}; try { kit=JSON.parse(res.headers.get('X-Kit')||'{}'); } catch(e){}
    const fname=((res.headers.get('Content-Disposition')||'').match(/filename="?([^";]+)/)||[])[1]||'starter.miz';
    const result=Object.freeze({rc,source,kit,fname,warn:res.headers.get('X-Warnings')});
    saveDownload(blob,fname);
    MISSION_RESULTS[source]=result; LAST_GEN_RECIPE=rc;
    ga('generate',{source}); showKit(result,box);
    status('Download started — your Mission Kit is ready.');
    return result;
  } catch(e){ status('Error: '+e.message); return null; }
  finally { GENERATING=false; if(btn) btn.innerHTML=oldLabel; syncGenerationButtons(); }
}
async function downloadDocument(btn, result, endpoint, label, fallback){
  const rc=freezeRecipe(result ? result.rc : recipe());
  const source=result ? result.source : 'builder';
  const st=btn.closest('.revlist')?.querySelector('.kitstatus')||document.getElementById('status');
  const status=text=>{ if(st) st.textContent=text; };
  btn.disabled=true; status('Building '+label+'…');
  try{
    const res=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({recipe:rc,source,visitor:visitorId()})});
    if(!res.ok){ status('Error: '+await responseError(res)); return; }
    const blob=await res.blob();
    const fname=((res.headers.get('Content-Disposition')||'').match(/filename="?([^";]+)/)||[])[1]||fallback;
    saveDownload(blob,fname); status(label+' download started.');
  } catch(e){ status('Error: '+e.message); }
  finally { btn.disabled=false; }
}
async function downloadKneeboard(btn, result=null){
  ga('kneeboard_download');
  return downloadDocument(btn,result,'/api/kneeboard','Kneeboard pack','kneeboard_pack.zip');
}
async function downloadBrief(btn, result=null){
  return downloadDocument(btn,result,'/api/brief','Briefing pack','briefing_pack.zip');
}

return {
  functions: {kitRows, wireKitButtons, showKit, closeKit, freezeRecipe, syncGenerationButtons, responseError, saveDownload, generateMission, downloadDocument, downloadKneeboard, downloadBrief},
  get lastRecipe() { return LAST_GEN_RECIPE; },
  get busy() { return GENERATING; },
  results: MISSION_RESULTS
};
}
