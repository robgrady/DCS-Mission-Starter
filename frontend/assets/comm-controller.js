/** createCommController: explicit state, environment and cross-controller actions. */
function createCommController({state, getOptions, callbacks, environment}) {
const {document, window, localStorage, fetch, navigator, location, history, prompt} = environment;
const S = state;
const OPT = new Proxy({}, {get: (_, key) => getOptions()?.[key]});
const { SUP_NAMES, sel, updateRail, recipe, saveState } = callbacks;
// --- Comm plan table (missiongen/commplan.py) --------------------------------
// S.comms holds {row: MHz} — only the cells the pilot overwrote. The server
// describes the table (/api/commplan) so the rows, the channels and which
// radio holds them are DATA from the same module the engine uses, not a
// second copy typed in here; it also validates (/api/commplan/validate) with
// the exact rules Recipe.validate applies, so a red cell here is a 400 there.
// Profiles are this browser's localStorage and nothing else: a profile is a
// way to FILL the cells, the recipe carries the cells, and the share link
// carries the recipe — so a link reproduces the mission without the profile.
let COMM = { key:null, rows:[], radios:[], errs:{}, warns:{}, timer:null };
const COMM_NEEDS = { bb_carrier:'Carrier', bb_tanker:'Tanker', bb_awacs:'AWACS', carrier_cap:'Carrier CAP', carrier_aew:'Carrier AEW' };
function commPresent(){
  const g = id => !!document.getElementById(id)?.checked;
  return { aircraft: document.getElementById('aircraft').value,
           bb_tanker: g('bb_tanker'), bb_awacs: g('bb_awacs'), bb_carrier: g('bb_carrier'),
           carrier_cap: g('bb_carrier') && g('carrier_cap'),
           carrier_aew: g('bb_carrier') && g('carrier_aew') };
}
function commOverrides(){
  const o = {};
  for (const [k,v] of Object.entries(S.comms||{})){
    if (v === '' || v == null) continue;
    const f = parseFloat(v); if (Number.isFinite(f)) o[k] = f; else o[k] = v;   // bad text still goes up: the server names it
  }
  return Object.keys(o).length ? o : null;
}
function commSummary(){
  const o = commOverrides(); if (!o) return "standard ladder";
  const n = Object.keys(o).length;
  const names = COMM.rows.filter(r=>o[r.key]!=null).map(r=>`${r.agency} ${fmtMhz(o[r.key])}`);
  return names.length ? names.join(' · ') : `${n} custom`;
}
function fmtMhz(v){ const f = parseFloat(v); return Number.isFinite(f) ? f.toFixed(3) : String(v); }
function toggleComms(h){
  const s = document.getElementById('sec_comms'); s.classList.toggle('folded');
  h.setAttribute('aria-expanded', String(!s.classList.contains('folded')));
}
function setCommOverrides(o, unfold){
  S.comms = {}; for (const [k,v] of Object.entries(o||{})) S.comms[k] = v;
  if (unfold && Object.keys(S.comms).length){
    const s = document.getElementById('sec_comms'); s.classList.remove('folded');
    s.querySelector('h2')?.setAttribute('aria-expanded','true');
  }
  renderCommRows(); commValidateSoon();
}
async function refreshCommTable(){
  const p = commPresent(); const key = JSON.stringify(p);
  if (key === COMM.key) return;
  COMM.key = key;
  try {
    const q = new URLSearchParams(Object.entries(p).map(([k,v])=>[k, String(v)]));
    const d = await (await fetch('/api/commplan?' + q)).json();
    if (COMM.key !== key) return;                 // a newer request is in flight
    COMM.rows = d.rows || []; COMM.radios = d.radios || [];
  } catch(e){ COMM.rows = []; COMM.radios = []; }
  renderCommRows(); commValidateSoon();
}
function renderCommRows(){
  const tb = document.getElementById('commrows'); if (!tb) return;
  const hv = document.getElementById('hv_comms'); if (hv) hv.textContent = commSummary();
  if (!COMM.rows.length){ tb.innerHTML = '<tr><td colspan="5" class="note">Pick an aircraft to see its comm plan.</td></tr>'; return; }
  const radios = COMM.radios.map(r=>`R${r.id}`).join('+');
  tb.innerHTML = COMM.rows.map(r=>{
    const v = S.comms[r.key]; const set = v != null && v !== '';
    const ch = r.channel === 'last' ? 'last' : (r.channel==null ? '—' : 'CH '+r.channel);
    const locked = !r.editable;
    let note = '';
    if (locked) note = '<span class="lock">fixed by regulation</span>';
    else if (r.kind === 'absent') note = `off${r.needs ? ' — needs ' + (COMM_NEEDS[r.needs] || SUP_NAMES[r.needs] || r.needs) : ''}`;
    else if (r.key === 'flight_common') note = 'DCS loads the flight freq on CH 1';
    else if (r.key === 'aew' && r.channel === 3) note = 'CH 3 while there is no AWACS';
    if (COMM.errs[r.key]) note = `<span class="err">${COMM.errs[r.key]}</span>`;
    else if (COMM.warns[r.key]) note = `<span class="wrn">${COMM.warns[r.key]}</span>` + (note ? ' · ' + note : '');
    const radio = r.held ? radios : (r.kind === 'absent' ? '' : (COMM.radios.length ? 'card only' : '—'));
    const cls = (set ? 'set ' : '') + (COMM.errs[r.key] ? 'bad' : (COMM.warns[r.key] ? 'warn' : ''));
    return `<tr class="${r.kind}" data-k="${r.key}"><td class="ch">${ch}</td>`
      + `<td class="ag" title="${r.blurb.replace(/"/g,'&quot;')}"><b>${r.agency}</b><small>${r.blurb}</small></td>`
      + `<td class="def">${fmtMhz(r.default)}</td>`
      + `<td><input type="text" inputmode="decimal" class="${cls}" data-k="${r.key}" value="${set ? String(v) : ''}" placeholder="${fmtMhz(r.default)}" ${locked ? 'disabled' : ''} aria-label="${r.agency} frequency, MHz"></td>`
      + `<td class="ch radio">${radio}</td><td class="note">${note}</td></tr>`;
  }).join('');
  tb.querySelectorAll('input').forEach(inp=>{
    inp.addEventListener('input', ()=>{
      const k = inp.dataset.k, v = inp.value.trim();
      if (v === '') delete S.comms[k]; else S.comms[k] = v;
      inp.classList.toggle('set', v !== '');
      commValidateSoon(); updateRail(); saveState();
      const hv2 = document.getElementById('hv_comms'); if (hv2) hv2.textContent = commSummary();
    });
    inp.addEventListener('blur', ()=>{ const f = parseFloat(inp.value); if (Number.isFinite(f) && inp.value.trim() !== '') { inp.value = f.toFixed(3); S.comms[inp.dataset.k] = inp.value; } });
  });
  commProfilesRender();
}
function commValidateSoon(){ clearTimeout(COMM.timer); COMM.timer = setTimeout(commValidate, 350); }
async function commValidate(){
  const o = commOverrides();
  COMM.errs = {}; COMM.warns = {};
  const note = document.getElementById('commnote');
  if (!o){ if (note) note.textContent = ''; paintCommMarks(); return; }
  try {
    const d = await (await fetch('/api/commplan/validate', {method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({comms:o, aircraft: document.getElementById('aircraft').value})})).json();
    for (const e of d.errors||[]) if (e.key) COMM.errs[e.key] = e.msg;
    for (const w of d.warnings||[]) if (w.key) COMM.warns[w.key] = w.msg;
    if (note) note.textContent = (d.errors||[]).length
      ? 'Fix the red cells — Build will refuse this table as it stands.'
      : `${Object.keys(d.clean||{}).length} override${Object.keys(d.clean||{}).length===1?'':'s'} — the card, kneeboard, DTC and every station follow.`;
  } catch(e){ if (note) note.textContent = ''; }
  paintCommMarks();
}
function paintCommMarks(){
  // re-render notes/marks without rebuilding inputs under the cursor
  document.querySelectorAll('#commrows tr').forEach(tr=>{
    const k = tr.dataset.k, inp = tr.querySelector('input'), r = COMM.rows.find(x=>x.key===k); if (!r) return;
    inp.classList.toggle('bad', !!COMM.errs[k]); inp.classList.toggle('warn', !COMM.errs[k] && !!COMM.warns[k]);
    const td = tr.querySelector('td.note'); const radios = COMM.radios.map(x=>`R${x.id}`).join('+');
    let base = '';
    if (!r.editable) base = '<span class="lock">fixed by regulation</span>';
    else if (r.kind === 'absent') base = `off${r.needs ? ' — needs ' + (COMM_NEEDS[r.needs] || SUP_NAMES[r.needs] || r.needs) : ''}`;
    else if (r.key === 'flight_common') base = 'DCS loads the flight freq on CH 1';
    else if (r.key === 'aew' && r.channel === 3) base = 'CH 3 while there is no AWACS';
    const radio = r.held ? radios : (r.kind === 'absent' ? '' : (COMM.radios.length ? 'card only' : '—'));
    let mark = COMM.errs[k] ? `<span class="err">${COMM.errs[k]}</span>` : (COMM.warns[k] ? `<span class="wrn">${COMM.warns[k]}</span>` : '');
    tr.querySelector('td.radio').textContent = radio;
    td.innerHTML = [mark, COMM.errs[k] ? '' : base].filter(Boolean).join(' · ');
  });
}
// --- profiles: this browser only -------------------------------------------
function commProfiles(){ try { return JSON.parse(localStorage.getItem('ms_commprofiles')||'{}') || {}; } catch(e){ return {}; } }
function commProfilesSave(p){ try { localStorage.setItem('ms_commprofiles', JSON.stringify(p)); } catch(e){} }
function commProfilesRender(){
  const sel = document.getElementById('commprof'); if (!sel) return;
  const cur = sel.value; const p = commProfiles();
  sel.innerHTML = '<option value="">— none —</option>' + Object.keys(p).sort().map(n=>`<option value="${n.replace(/"/g,'&quot;')}">${n}</option>`).join('');
  if (cur && p[cur]) sel.value = cur;
  document.getElementById('commdel').disabled = !sel.value;
}
function initCommUI(){
  const sel = document.getElementById('commprof'); if (!sel) return;
  sel.addEventListener('change', ()=>{
    const p = commProfiles()[sel.value];
    document.getElementById('commdel').disabled = !sel.value;
    if (p){ setCommOverrides(p, true); updateRail(); saveState(); }
  });
  document.getElementById('commsave').onclick = ()=>{
    const o = commOverrides(); if (!o){ alertNote('Nothing to save — every cell is still the standard ladder.'); return; }
    const name = (prompt('Name this comm profile (saved in this browser only):', sel.value || 'Squadron SOP') || '').trim();
    if (!name) return;
    const p = commProfiles(); p[name] = o; commProfilesSave(p); commProfilesRender(); sel.value = name;
    document.getElementById('commdel').disabled = false;
  };
  document.getElementById('commdel').onclick = ()=>{
    const p = commProfiles(); if (!sel.value || !p[sel.value]) return;
    delete p[sel.value]; commProfilesSave(p); sel.value = ''; commProfilesRender();
  };
  document.getElementById('commreset').onclick = ()=>{ setCommOverrides({}, false); sel.value=''; document.getElementById('commdel').disabled = true; updateRail(); saveState(); };
  document.getElementById('commexport').onclick = async ()=>{
    const o = commOverrides() || {};
    try { await navigator.clipboard.writeText(JSON.stringify(o, null, 2)); alertNote('Copied — paste it into a recipe as "comms", or send it to a wingman.'); }
    catch(e){ alertNote(JSON.stringify(o)); }
  };
  function alertNote(t){ const n = document.getElementById('commnote'); if (n) n.textContent = t; }
}

return { COMM, commOverrides, commPresent, commProfiles, commProfilesRender, commProfilesSave, commSummary, commValidate, commValidateSoon, fmtMhz, initCommUI, paintCommMarks, refreshCommTable, renderCommRows, setCommOverrides, toggleComms };
}
