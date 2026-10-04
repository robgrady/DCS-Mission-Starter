const S = { map:null, era:null, template:null, kind:null, corridors:[], comms:{} };
// Flightline modes: paper is the default identity; night is the kit's
// cockpit-adjacent set for people flying in dark rooms. Persisted locally —
// a display preference is device state, not recipe state, so it does NOT go
// in share links: your night habit should not restyle a friend's browser.
(function(){ try { var m = localStorage.getItem('fl_mode');
  if (m === 'night') document.body.dataset.mode = 'night'; } catch(e){} bootModeBtn(); })();
function bootModeBtn(){ var b = document.getElementById('modebtn'); if (!b) return;
  b.innerHTML = document.body.dataset.mode === 'night'
    ? '<svg class="icon"><use href="#i-sun"/></svg> LIGHT'
    : '<svg class="icon"><use href="#i-moon"/></svg> DARK'; }
function flipMode(){
  var m = document.body.dataset.mode === 'night' ? 'paper' : 'night';
  document.body.dataset.mode = m;
  try { localStorage.setItem('fl_mode', m); } catch(e){}
  bootModeBtn(); }
// each block renders into a target container on its screen (5th field)
const BLOCKS = [
  ["bb_dressing","Airfield dressing","Static aircraft, GSE, infrastructure on real stands", true, "tog_dress"],
  ["bb_sams","Air defenses","Complete era-correct SAM sites + SHORAD", true, "tog_threat"],
  ["bb_carrier","Carrier strike group","CVN + escorts on BRC, TACAN 71X / ICLS 11 / Link4 (blue, coastal maps)", false, "tog_carrier"],
  ["bb_tanker","Tanker","Racetrack, TACAN + freq assigned", true, "sup_air"],
  ["bb_awacs","AWACS","On station behind friendly lines", true, "sup_air"],
  ["bb_ambient","Ambient air traffic","AI transports starting up and flying between friendly fields", true, "sup_air"],
  ["bb_pattern","Aircraft in the pattern","A few AI aircraft recovering or departing at YOUR field as the mission starts — pick the leg, the type and how many", false, "tog_pattern"],
  ["bb_farps","Functional FARPs","Pads + fuel/ammo/command/comms so rearm-refuel works (helo eras)", false, "sup_air"],
  ["bb_targets","Strike target packages","Depot / convoy / C2 site placed in the enemy rear with trigger zones", false, "sup_tgt"],
  ["bb_range","Practice range","Bombing ring + strafe line in the friendly rear", false, "sup_tgt"],
  ["bb_route","Automatic waypoints","Build a flight plan to the target and back — WP1 &rarr; IP &rarr; TARGET &rarr; home, on the F10 map, in the jet's nav system and on a kneeboard leg card. On Nevada the plan flies the Nellis corridors (FLEX, Sally, Alamo, FYTTR, the recoveries); on Syria the Levant roads (the coast and the Bekaa, J14 and Hermon, Akrotiri's SIDs, W74 out of Incirlik, L200 to Al-Tanf); on Cold War Germany the Central Region of 1985 (the ADIZ, the HAWK belt's transit routes to the Fulda Gap and Helmstedt, the Berlin corridors, the GDR's own flight lines &mdash; either side of the line) &mdash; see the corridor charts: <a href='/api/corridors/nevada/chart.svg' target='_blank' rel='noopener'>NTTR</a> &middot; <a href='/api/corridors/syria/chart.svg' target='_blank' rel='noopener'>Levant</a> &middot; <a href='/api/corridors/germany/chart.svg' target='_blank' rel='noopener'>Central Region</a>. Needs a target package. Off by default: normally we set the stage and you write the play.", false, "sup_tgt"],
  ["bb_comms","Comms card","Non-conflicting freq/TACAN plan in briefing", true, "sup_brief"],
  ["bb_briefing","Starter briefing","Situation + contents summary", true, "sup_brief"],
  ["bb_kneeboard","Nav chart kneeboard","Comms card, airfield data + theater overview pages in the jet", true, "sup_brief"],
  ["bb_navpoints","Nav reference points","Named landmarks (Belted Peak, Student Gap...) on F10 map + kneeboard", true, "sup_brief"],
  ["bb_historical_airspace","Historical airspace","Historical and illustrative training airspace — drawn on F10; accuracy and reference dates are in the brief and kneeboard", false, "sup_brief"],
  ["bb_alignment","Theater identity (nation alignment)","Each airbase dresses as its real owning nation — country, aircraft types, liveries (Akrotiri = RAF, Ramat David = Israel...)", true, "tog_dress"],
];

// --- share links: recipe <-> base64url(JSON of non-default fields) ---
const RECIPE_DEFAULTS = {map:"caucasus",era:"coldwar",coalition:"blue",aircraft:"F_16C_50",
  home_airbase:null,slots:1,veteran_wingmen:0,start:"cold",time_of_day:"day",weather:"clear",density:"normal",
  dress_fill:null,dress_aircraft:true,dress_gse:true,dress_infra:true,dress_theme:null,
  map_layers:null,dress_overrides:{},dress_aircraft_mode:"static",dress_mix:null,
  dress_livery_style:"squadron",ramp_heavies:"auto",
  player_arm:true,player_load:"standard",
  threat_intensity:3,threat_tier:"auto",
  bb_dressing:true,bb_sams:true,bb_tanker:true,bb_awacs:true,bb_comms:true,bb_briefing:true,
  bb_kneeboard:true,bb_carrier:false,bb_ambient:true,bb_navpoints:true,bb_farps:false,bb_targets:false,bb_range:false,
  bb_route:false,
  timing_anchor:"takeoff",timing_at:null,timing_hold_min:0,timing_coach:false,timing_package:false,
  bb_pattern:false,pattern_mode:"landing",pattern_kind:"fighter",pattern_count:2,pattern_lineup:false,
  bb_historical_airspace:false,bb_alignment:true,
  carrier_hull:null,carrier_layout:"recovery",carrier_deck_aircraft:[],carrier_equipment:true,
  carrier_cap:false,carrier_aew:false,carrier_strike:false,template:null,crew_difficulty:"qualified",
  callsign:null,seed:1,mission_kind:"open",comms:null};
// Engine settings without Builder controls must survive opening a shared
// recipe. Do not add their defaults to a template recipe: omission lets the
// template supply its own defaults on the server.
const RECIPE_ENGINE_FIELDS = ['lineup','coach_gates','coach_ring','cq_ride',
  'formation','tanker_type','bb_branding','bb_dtc','bb_bfm','bfm_setup',
  'target_packages','published_corridors','check_ride','player_fit'];

// --- Mission kind (v1.45.0) -------------------------------------------------
// The Builder's missing first question. Each kind stamps DEFAULTS onto the
// building blocks — it never locks anything, so every later screen remains
// fully editable and a hand-edited recipe still wins. `what` is printed under
// the cards the moment you pick, because a preset that changes settings you
// can't see is exactly the "hidden" problem this screen was built to solve.
// "open" reproduces today's behavior byte-for-byte, so it stays the default
// and no existing share link changes meaning.
const MISSION_KINDS = [
  {k:"open", label:"Open tasking", blurb:"A living theater, nothing assigned",
   what:"No targets marked and no route placed — the theater is live and the tasking is yours.",
   patch:{bb_targets:false, bb_range:false}},
  {k:"a2a", label:"Air-to-air", blurb:"Enemy fighters up on the threat axis",
   what:"Enemy CAP on the threat axis with era-correct, briefed loadouts. AWACS and a tanker on station.",
   patch:{bb_sams:true, threat_intensity:3, bb_targets:false, bb_range:false,
          bb_tanker:true, bb_awacs:true}},
  {k:"strike", label:"Strike", blurb:"Targets in the enemy rear, defended",
   what:"Target packages in the enemy rear behind a SAM belt worth penetrating. Tanker and AWACS on station.",
   patch:{bb_targets:true, bb_sams:true, threat_intensity:3, threat_tier:"auto",
          bb_tanker:true, bb_awacs:true, bb_range:false}},
  {k:"cas", label:"Close air support", blurb:"Low, in the guns, over the target",
   what:"Targets defended by AAA instead of SAMs — you can fly over it high, but you have to come down into the guns to hit anything.",
   patch:{bb_targets:true, bb_sams:true, threat_tier:"guns", threat_intensity:3,
          bb_tanker:true, bb_awacs:true, bb_range:false}},
  {k:"sead", label:"SEAD", blurb:"Hunt the radars first",
   what:"A heavy, long-range SAM belt with targets behind it. Bring anti-radiation missiles.",
   patch:{bb_targets:true, bb_sams:true, threat_tier:"heavy", threat_intensity:4,
          bb_tanker:true, bb_awacs:true, bb_range:false}},
  {k:"carrier", label:"Carrier ops", blurb:"Off the deck of a real strike group",
   what:"You start on the deck of a real strike group, with the air wing's tanker and Hawkeye up.",
   patch:{bb_carrier:true, bb_tanker:true, bb_awacs:true, bb_targets:false,
          bb_range:false}},
  {k:"training", label:"Training", blurb:"Range work with the threats turned down",
   what:"A practice range in the friendly rear and aircraft in the pattern at your field, with air defenses off.",
   patch:{bb_range:true, bb_sams:false, threat_intensity:1, bb_targets:false,
          bb_pattern:true, bb_ambient:true}},
];

function kindDef(k){ return MISSION_KINDS.find(m=>m.k===k) || MISSION_KINDS[0]; }

// Carrier ops needs a carrier-capable airframe AND a map with a sea to sail
// on. Rather than let the card fail after the fact, it's disabled with the
// reason on it — a control that explains why it can't be used beats one that
// silently doesn't work.
function kindAvailable(k){
  if (k !== "carrier") return true;
  try { return !!(OPT && OPT.maps[S.map] && OPT.maps[S.map].carrier !== false
                  && document.getElementById('bb_carrier')
                  && !document.getElementById('bb_carrier').closest('.block')?.classList.contains('dis')); }
  catch(e){ return true; }
}

function renderKinds(){
  const box = document.getElementById('kinds');
  if (!box) return;
  box.innerHTML = '';
  for (const m of MISSION_KINDS){
    const ok = kindAvailable(m.k);
    const c = el(`<div class="card${ok?'':' dis'}${S.kind===m.k?' sel':''}" data-k="${m.k}">`
      + `<b>${m.label}</b><small>${ok ? m.blurb : 'Needs a carrier-capable jet and a coastal map'}</small></div>`);
    if (ok) c.onclick = ()=>pickKind(m.k);
    box.appendChild(c);
  }
  document.getElementById('kind_what').innerHTML =
    S.kind ? `<b>${kindDef(S.kind).label}:</b> ${kindDef(S.kind).what}`
           : 'Pick one and this line will tell you exactly what it changed.';
}

// Applying a kind writes real values into the real controls, so the change is
// visible on the screens that own them rather than hidden in a parallel state.
function pickKind(k, silent){
  S.engineSettings = {};
  if (!silent){
    S.template=null;
    const custom=document.querySelector('#templates .card[data-k=""]');
    if(custom) sel(document.getElementById('templates'),custom);
  }
  S.kind = k;
  const m = kindDef(k);
  for (const [id, v] of Object.entries(m.patch)){
    const el_ = document.getElementById(id);
    if (!el_) continue;
    if (el_.type === 'checkbox'){
      if (el_.closest('.block')?.classList.contains('dis')) continue;  // unavailable here
      el_.checked = !!v;
    } else {
      el_.value = v;
    }
    el_.dispatchEvent(new Event('change', {bubbles:true}));
  }
  if (m.patch.threat_intensity != null && typeof setIntensityLabel === 'function')
    setIntensityLabel(m.patch.threat_intensity);
  if (typeof refreshCarrierUI === 'function') refreshCarrierUI();
  if (typeof refreshPatternUI === 'function') refreshPatternUI();
  renderKinds();
  if (!silent){ updateRail(); buildReview(); sum(); }
}

// Authentic default flight callsign per airframe (mirror of callsigns.json —
// used for the placeholder + provenance hint; the engine holds the truth).
const AC_CALLSIGN = {
  F_14A_135_GR:["Gypsy","VF-32 Swordsmen — Gulf of Sidra '89"],
  F_14A_135_GR_Early:["Fast Eagle","VF-41 Black Aces — Sidra '81"],
  F_14A_95_GR:["Gypsy","VF-32 Swordsmen"],
  F_14B:["Victory","VF-103 Jolly Rogers"], F_14B_U:["Victory","VF-103 Jolly Rogers"],
  FA_18C_hornet:["Chippy","VFA-195 Dambusters"], AV8BNA:["Blacksheep","VMA-214"],
  F_16C_50:["Basher","USAF — Basher 52, Bosnia '95"], F_15C:["Citgo","58th TFS, Desert Storm"],
  F_15ESE:["Chevron","Strike Eagle community"], F_4E_45MC:["Oyster","555th TFS — 10 May 1972"],
  F_100D:["Misty","the Misty FACs flew the Hun"], A_10A:["Hawg",""], A_10C:["Hawg",""],
  A_10C_2:["Hawg",""], F_5E_3:["Snake",""], F_5E_3_FC:["Snake",""],
  F_86F_Sabre:["Cadillac","4th FIW, Korea"], F_86F_FC:["Cadillac","4th FIW, Korea"],
  AH_64D_BLK_II:["Crazyhorse","1-227th ARB"], UH_1H:["Firebird",""], CH_47Fbl1:["Varsity",""],
  M_2000C:["Rage",""], Mirage_F1CE:["Rage",""], AJS37:["Petter Red","Flygvapnet"],
  P_51D:["Horseback","4th FG"], F_51D:["Horseback","4th FG"], P_47D_30:["Keyworth",""],
  SpitfireLFMkIX:["Dogsbody","Bader's call"], MosquitoFBMkVI:["Cranbrook",""],
  MiG_21Bis:["231","bort number"], MiG_15bis:["325","bort number"], MiG_15bis_FC:["325","bort number"],
  MiG_19P:["404","bort number"], MiG_29A:["121","bort number"], MiG_29S:["121","bort number"],
  Su_25T:["252","bort number"], Su_27:["501","bort number"], Su_33:["88","bort number"],
  Ka_50:["23","bort number"], Ka_50_3:["23","bort number"], Mi_24P:["35","bort number"],
  Mi_8MT:["48","bort number"], Bf_109K_4:["Blue 4","schwarm"], FW_190D9:["Green 1","schwarm"],
  FW_190A8:["Green 1","schwarm"]};

// --- anonymous visitor id (v1.43.0) ---------------------------------------
// A random UUID this browser makes up about ITSELF. Not derived from anything
// — no IP, no fingerprint — and stored hashed on the server. It answers only
// "how many people, and do they come back?". Honors Do Not Track without
// asking, and the About panel has a one-click off switch.
function dntOn(){ try{ return navigator.doNotTrack==='1'||window.doNotTrack==='1'
  ||navigator.msDoNotTrack==='1'; }catch(e){ return false; } }
function analyticsOff(){ try{ return localStorage.getItem('ms_noanalytics')==='1'; }
  catch(e){ return false; } }
function visitorId(){
  if (dntOn() || analyticsOff()) return null;
  try{
    let v = localStorage.getItem('ms_vid');
    if (!v){ v = (crypto.randomUUID ? crypto.randomUUID()
                 : String(Date.now())+Math.random().toString(16).slice(2));
             localStorage.setItem('ms_vid', v); }
    return v;
  }catch(e){ return null; }   // private mode: count as opted out
}
function setAnalytics(on){
  try{
    if (on) localStorage.removeItem('ms_noanalytics');
    else { localStorage.setItem('ms_noanalytics','1'); localStorage.removeItem('ms_vid'); }
  }catch(e){}
  renderPrivacy();
}
function renderPrivacy(){
  const el = document.getElementById('privacystate'); if(!el) return;
  const dnt = dntOn(), off = analyticsOff();
  // SAYS WHICH COUNTER IT GOVERNS. It governs ours. Letting "Counting is off"
  // stand unqualified while Google Analytics kept running would be a switch
  // that lies about what it did, which is worse than having no switch.
  el.innerHTML = dnt
    ? "Your browser sends <b>Do Not Track</b> — <b>our</b> counting is off for this browser. "
      + "Google Analytics does not read that signal; use a content blocker to stop it."
    : (off
      ? "<b>Our</b> counting is <b>off</b> for this browser. Google Analytics is unaffected. "
        + "<a href=\"#\" onclick=\"setAnalytics(true);return false\">Turn ours back on</a>"
      : "<b>Our</b> counting is <b>on</b>: an anonymous id for this browser, so we can tell how "
        + "many people use this and whether they come back. No IP, no account, no name. "
        + "<a href=\"#\" onclick=\"setAnalytics(false);return false\">Turn ours off</a>");
}

function defaultCallsign(){
  const k = document.getElementById('aircraft')?.value;
  const e = AC_CALLSIGN[k];
  if (e) return e;
  return document.getElementById('coalition')?.value==='red' ? ["201","bort number"] : ["Colt","NATO pool"];
}
document.addEventListener('DOMContentLoaded', ()=>{ const c=document.getElementById('callsign'); if(c) c.addEventListener('input', refreshCallsign); });
function refreshCallsign(){
  const el = document.getElementById('callsign'); if(!el) return;
  const [cs, unit] = defaultCallsign();
  el.placeholder = cs;
  const hint = document.getElementById('cs_hint');
  // DCS's radio speaks eight fighter names. Anything else is mapped to one of
  // them (stably, per name) and the brief keeps yours as the squadron's own.
  const DCS_POOL = ['Enfield','Springfield','Uzi','Colt','Dodge','Ford','Chevy','Pontiac'];
  const typed = (el.value||'').trim();
  const shown = typed || cs;
  const isPool = DCS_POOL.some(n => n.toLowerCase() === shown.toLowerCase());
  const isNum = /^\d+$/.test(shown);
  const note = (isPool || isNum) ? '' :
    ` · DCS's radio speaks only ${DCS_POOL.join(', ')}; "${shown}" is mapped to one of them and kept in the brief as the squadron's own.`;
  if (hint) hint.textContent = (unit ? `${cs} — ${unit}` : cs) + note;
}


let OPT = null;
let NAV_READY = false;
let CURRENT_VIEW = 'entry';

function cardState(c){
  const disabled=(c.classList.contains('dis') && !c.dataset.vote)||c.classList.contains('dim');
  if(c.tagName==='BUTTON') c.disabled=disabled;
  c.setAttribute('role','button'); c.tabIndex=disabled ? -1 : 0;
  c.setAttribute('aria-disabled',String(disabled));
  if(c.classList.contains('card')) c.setAttribute('aria-pressed',String(c.classList.contains('sel')));
  if(c.classList.contains('rstep')) c.setAttribute('aria-current',c.classList.contains('active')?'step':'false');
}
function syncCardState(){ document.querySelectorAll('.card,.rstep,.rsub').forEach(cardState); }
function el(html){
  const d=document.createElement('div'); d.innerHTML=html;
  let node=d.firstElementChild;
  if(node.matches('.card,.rstep,.rsub')){
    const button=document.createElement('button'); button.type='button';
    for(const attr of node.attributes) button.setAttribute(attr.name,attr.value);
    button.innerHTML=node.innerHTML; node=button; cardState(node);
  }
  return node;
}

// Minimal, no-PII demand signal (see claude/analytics-plan.md: server-side,
// no IP, no identifiers). Fire-and-forget — a 404 or an ad-blocked request is
// harmless and must never affect the wizard.
function track(ev){
  try{
    const body = JSON.stringify({event: ev});
    if (navigator.sendBeacon)
      navigator.sendBeacon('/api/ev', new Blob([body], {type:'application/json'}));
    else
      fetch('/api/ev', {method:'POST', headers:{'Content-Type':'application/json'},
                        body, keepalive:true}).catch(()=>{});
  }catch(e){}
  ga(ev);            // the same signal, to the other ledger
}

// --- Google Analytics 4 -----------------------------------------------------
//
// `gtag` only exists when the server injected the tag, which it does only when
// GA_MEASUREMENT_ID is set on that deployment (see server/ga.py — a self-hosted
// copy gets no tag and no third-party request). So every call goes through
// here: absent gtag, this is a no-op, and NOTHING in the app may depend on it.
// An ad blocker removing gtag.js must not be able to break a button.
//
// Parameters are deliberately thin. `source` and `view` are low-cardinality
// values that make the event meaningful at all; the map, aircraft and era of a
// generated mission are NOT sent, because the server-side ledger already
// records exactly that against the recipe and sending it twice to two
// different places is how two numbers start disagreeing.
function ga(name, params){
  try{
    if (typeof gtag !== 'function') return;
    gtag('event', name, params || {});
  }catch(e){}
}

// ===== R1: aircraft have names, not just designations =====
// The picker rendered raw pydcs type ids ("AV8BNA", "F_15ESE"), so people
// scanned 75 designations looking for "the Harrier". One table, used by the
// picker and by Library search — designation stays, the name comes with it.
const AC_NAME = {
  A_10A:"Warthog", A_10C:"Warthog", A_10C_2:"Warthog II",
  AH_64D_BLK_II:"Apache", AJS37:"Viggen", AV8BNA:"Harrier",
  Bf_109K_4:"Messerschmitt", C_101CC:"Aviojet", C_101EB:"Aviojet",
  C_130J_30:"Super Hercules", CH_47Fbl1:"Chinook", F_100D:"Super Sabre",
  F_14A_135_GR:"Tomcat", F_14A_135_GR_Early:"Tomcat", F_14A_95_GR:"Tomcat",
  F_14B:"Tomcat", F_14B_U:"Tomcat", F_15C:"Eagle", F_15ESE:"Strike Eagle", F_16C_50:"Viper",
  F_4E_45MC:"Phantom II", F_5E_3:"Tiger II", F_5E_3_FC:"Tiger II",
  F_86F_FC:"Sabre", F4U_1D:"Corsair", FA_18C_hornet:"Hornet",
  FW_190A8:"Butcher Bird", FW_190D9:"Dora", I_16:"Ishak", J_11A:"Flanker-B+",
  JF_17:"Thunder", Ka_50:"Black Shark", Ka_50_3:"Black Shark 3",
  L_39C:"Albatros", L_39ZA:"Albatros", La_7:"Lavochkin", M_2000C:"Mirage 2000",
  MB_339APAN:"Frecce Tricolori", Mi_24P:"Hind", Mi_8MT:"Hip",
  MiG_15bis:"Fagot", MiG_15bis_FC:"Fagot", MiG_19P:"Farmer",
  MiG_21Bis:"Fishbed", MiG_29A:"Fulcrum", MiG_29G:"Fulcrum", MiG_29S:"Fulcrum",
  Mirage_F1BE:"Mirage F1", Mirage_F1CE:"Mirage F1", Mirage_F1EE:"Mirage F1",
  MosquitoFBMkVI:"Mosquito", OH58D:"Kiowa Warrior",
  P_47D_30:"Thunderbolt (Jug)", P_47D_30bl1:"Thunderbolt (Jug)",
  P_47D_40:"Thunderbolt (Jug)", P_51D:"Mustang", P_51D_30_NA:"Mustang",
  SA342L:"Gazelle", SA342M:"Gazelle", SA342Minigun:"Gazelle",
  SA342Mistral:"Gazelle", SpitfireLFMkIX:"Spitfire", SpitfireLFMkIXCW:"Spitfire",
  Su_25:"Frogfoot", Su_25T:"Frogfoot", Su_27:"Flanker", Su_33:"Flanker-D",
  TF_51D:"Mustang (two-seat)", UH_1H:"Huey",
};
// The raw pydcs type id is a filename, not a designation: "FA-18C_hornet",
// "F-16C_50", "AH-64D_BLK_II". Underscores read as noise (the same complaint
// R1 fixed for names), and the trailing token is often just the popular name
// again -- which we are about to print anyway. Clean it once, here, so the
// picker, the Library filter and every badge get the same tidy designation.
function acCleanId(id, name){
  let s = String(id || '');
  if (name){
    // "FA-18C_hornet" + "Hornet" -> "FA-18C". First word only, so
    // "Warthog II" does not try to eat the "II" off "A-10C_2".
    const tail = name.split(' ')[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    s = s.replace(new RegExp('[_ ]' + tail + '$', 'i'), '');
  }
  // Everything DCS ships already uses hyphens as the sub-variant separator
  // ("F-14A-135-GR"), so underscores become hyphens rather than spaces.
  return s.replace(/_/g, '-').replace(/-{2,}/g, '-').replace(/-+$/, '') || String(id || '');
}
// Picker/filter text: designation first (so the list still sorts and clusters
// the way a pilot expects), name second.
function acDisplay(key, id){
  const name = AC_NAME[key];
  return name ? `${acCleanId(id, name)} · ${name}` : acCleanId(id, null);
}

// ===== R3: "Who's flying" =====
// Multiplayer used to hide behind a numeric "Slots" box, so nobody found it.
// It's a card group now — same shape as Era, on the front of the Flight screen.
// The hidden #slots input stays the DOM source of truth: recipe() reads it and
// applyRecipe() writes it, so share links and scenario presets are untouched.
const FLIGHT_MODES = [
  [1, "Just me",  "Single player. Fly it solo, offline."],
  [2, "2-ship",   "2 aircraft, same airframe. Choose human seats or veteran AI below."],
  [3, "3-ship",   "3 aircraft, same airframe. Choose human seats or veteran AI below."],
  [4, "4-ship",   "4 aircraft, same airframe. Choose human seats or veteran AI below."],
];
function initFlightMode(){
  const box = document.getElementById('flightmode');
  for (const [n, label, hint] of FLIGHT_MODES){
    const c = el(`<div class="card" data-k="${n}"><b>${label}</b><small>${hint}</small></div>`);
    c.onclick = ()=>{ setFlightMode(n); sum(); };
    box.appendChild(c);
  }
  // Mixed flight is real demand from feedback but has no engine support yet —
  // the builder makes ONE group of ONE airframe. Show it grayed so people stop
  // hunting for it, and log the click as a demand signal for the flights[] work.
  const mixed = el(`<div class="card dis" id="fm_mixed" data-vote="true"><b>Mixed flight</b>` +
                   `<small>Different aircraft in one flight — not yet</small></div>`);
  mixed.style.pointerEvents = 'auto';       // .dis kills clicks; we want this one
  mixed.style.cursor = 'not-allowed';
  mixed.onclick = ()=>{
    track('want_mixed_flight');
    mixed.querySelector('small').textContent = 'Noted — logged as a vote for this';
  };
  box.appendChild(mixed);
  setFlightMode(1);
}
function setFlightMode(n){
  document.getElementById('slots').value = n;
  document.querySelectorAll('#flightmode .card').forEach(c =>
    c.classList.toggle('sel', c.dataset.k === String(n)));
  refreshWingmen();
}
function refreshWingmen(){
  const select = document.getElementById('veteran_wingmen');
  const n = +document.getElementById('slots').value || 1;
  const fixed = !!S.engineSettings?.cq_ride || !!OPT.templates[S.template]?.aircraft_locked;
  const count = fixed ? 0 : Math.min(+select.value || 0, n-1);
  select.innerHTML = Array.from({length:fixed?1:n}, (_,i)=>`<option value="${i}">${i===0?'None — human seats':i+' veteran AI wingman'+(i===1?'':'s')}</option>`).join('');
  select.value = count; select.disabled = fixed || n===1;
  const humans = n-count;
  document.getElementById('wingmen_hint').textContent = fixed
    ? 'This authored flight uses fixed crew or recovery roles.'
    : n===1 ? 'Choose a 2-, 3- or 4-ship to add AI wingmen.'
    : `${humans===1?'You':humans+' human client seats'} + ${count} veteran AI ${count===1?'wingman':'wingmen'}. Veteran uses DCS High skill; wingmen fly in your group and respond to radio commands.`;
}
function flightModeLabel(){
  const n = +document.getElementById('slots').value || 1;
  const m = FLIGHT_MODES.find(f=>f[0]===n);
  const ai = +document.getElementById('veteran_wingmen').value || 0;
  return (m ? m[1] : `${n}-ship`) + (ai ? ` · ${ai} veteran AI` : '');
}

// ===== R4: threat presets =====
// "No threats" was reachable only by knowing to untick a building block, and
// "make it hard" meant reasoning about a 1-5 dial plus a system-level dropdown.
// These four cards set both at once; the dial below stays as the override.
// Sandbox also turns on strike target packages — an empty sky with nothing to
// shoot at isn't a sandbox, it's an empty map.
const THREAT_PRESETS = [
  ["sandbox","Sandbox","Nothing shoots back. Targets in the enemy rear to practice on.",
   {sams:false, intensity:1, tier:"auto", targets:true}],
  ["light","Light","A token CAP and older SAMs. Room to make mistakes.",
   {sams:true, intensity:2, tier:"light"}],
  ["standard","Standard","Period-correct defenses at normal density.",
   {sams:true, intensity:3, tier:"auto"}],
  ["contested","Contested","Layered belts and heavy CAP. Bring a plan.",
   {sams:true, intensity:5, tier:"heavy"}],
];
function initThreatPresets(){
  const box = document.getElementById('threatpresets');
  for (const [k,label,hint] of THREAT_PRESETS){
    const c = el(`<div class="card" data-k="${k}"><b>${label}</b><small>${hint}</small></div>`);
    c.onclick = ()=>applyThreatPreset(k);
    box.appendChild(c);
  }
  syncThreatPreset();
}
function applyThreatPreset(k){
  const p = THREAT_PRESETS.find(x=>x[0]===k); if(!p) return;
  const v = p[3];
  document.getElementById('bb_sams').checked = v.sams;
  const inten = document.getElementById('threat_intensity');
  inten.value = v.intensity; setIntensityLabel(v.intensity);
  document.getElementById('threat_tier').value = v.tier;
  if (v.targets) document.getElementById('bb_targets').checked = true;
  syncThreatPreset(); sum();
}
// Keep the cards honest: if someone moves the dial by hand, or a share link
// lands on a combination no preset produces, no card claims to be selected.
function syncThreatPreset(){
  const sams = document.getElementById('bb_sams')?.checked;
  const inten = +document.getElementById('threat_intensity').value;
  const tier = document.getElementById('threat_tier').value;
  const hit = THREAT_PRESETS.find(([,,,v]) =>
    v.sams === !!sams && (!v.sams || (v.intensity === inten && v.tier === tier)));
  document.querySelectorAll('#threatpresets .card').forEach(c =>
    c.classList.toggle('sel', !!hit && c.dataset.k === hit[0]));
}

// ===== R5: name the support assets =====
// The rail used to read "6 on", which tells you nothing and makes the screen
// un-skippable. Name what's actually on station instead.
const SUP_NAMES = {
  bb_tanker:"Tanker", bb_awacs:"AWACS", bb_ambient:"Ambient traffic",
  bb_pattern:"Pattern traffic", bb_farps:"FARPs", bb_targets:"Strike targets",
  bb_range:"Practice range", bb_comms:"Comms card", bb_briefing:"Briefing",
  bb_kneeboard:"Kneeboard", bb_navpoints:"Nav points",
  bb_historical_airspace:"Historical airspace",
};
function supportSummary(max){
  const on = Object.keys(SUP_NAMES)
    .filter(k=>document.getElementById(k)?.checked).map(k=>SUP_NAMES[k]);
  if (!on.length) return "nothing on";
  return on.length <= max ? on.join(' · ')
                          : on.slice(0,max).join(' · ') + ` +${on.length-max}`;
}
// Mode-aware close-out. Telling someone to drop a 2-ship build in Missions and
// hit Fly is wrong when multiple human seats remain: those are clients.
// A solo player with AI wingmen can fly offline. Also name on-station assets.
function postGenNote(){
  const n = +document.getElementById('slots').value || 1;
  const ai = +document.getElementById('veteran_wingmen').value || 0;
  const humans = n-ai;
  const side = document.getElementById('coalition').value;
  let s = humans > 1
    ? `${humans} client seats — host it (Multiplayer → New Server) or put it on your server; there's no single-player slot.`
    : 'Single-player — put it in Saved Games\\DCS\\Missions and hit Fly.';
  if(ai) s += ` ${ai} veteran AI ${ai===1?'wingman flies':'wingmen fly'} in your flight (High skill). Command them through the wingman radio menu.`;
  const air = [];
  if (document.getElementById('bb_tanker')?.checked && side==='blue' && S.era!=='wwii')
    air.push('Texaco 1-1 (tanker)');
  if (document.getElementById('bb_awacs')?.checked && S.era!=='wwii')
    air.push(side==='blue' ? 'Overlord 1-1 (AWACS)' : 'Overlord 1-1 (A-50 AWACS)');
  if (air.length)
    s += ` On station: ${air.join(' and ')} — TACAN and frequencies are on the comms card in the briefing.`;
  return s;
}

// Keep the sticky wizard nav sitting exactly on top of the status strip. The
// strip's height changed when the generate button moved out of it, and will
// change again if its copy wraps on a narrow window — so measure, don't guess.
function syncGenbarHeight(){
  const g = document.querySelector('.genbar');
  if (!g) return;
  const h = Math.round(g.getBoundingClientRect().height);
  if (h) document.documentElement.style.setProperty('--genbar-h', h + 'px');
}
window.addEventListener('resize', syncGenbarHeight);

async function init(){
  const loadError=document.getElementById('loaderror'), retry=document.getElementById('loadretry');
  retry.disabled=true; loadError.hidden=true;
  try{
    const res=await fetch('/api/options', {cache:'no-store'});
    if(!res.ok) throw new Error('Options request failed');
    OPT=await res.json();
  } catch(e){ loadError.hidden=false; retry.disabled=false; return; }
  if (OPT.version) document.getElementById('appver').textContent = 'v' + OPT.version;
  initGfxUI();
  initCommUI();
  const maps = document.getElementById('maps');
  for (const [k,v] of Object.entries(OPT.maps)){
    const c = el(`<div class="card" data-k="${k}"><b>${v.label}</b><small>${v.free?'Free terrain':'Paid terrain'}</small></div>`);
    c.onclick = ()=>{ if(S.map!==k) S.engineSettings={}; S.map=k; sel(maps,c); refreshEraGating(); fillHome(); refreshDressUI(); renderCorridors(); sum(); };
    maps.appendChild(c);
  }
  // Library era filter, built from OPT.eras rather than typed into the HTML.
  // It was static markup listing three eras and would have silently omitted
  // any fourth — the same "orphaned data" failure the corridor tests guard.
  const lfe = document.getElementById('lfEra');
  if (lfe && lfe.options.length <= 1)
    for (const [k,v] of Object.entries(OPT.eras))
      lfe.appendChild(el(`<option value="${k}">${v.label.replace(/\s*\(.*\)\s*$/,'')}</option>`));
  const eras = document.getElementById('eras');
  for (const [k,v] of Object.entries(OPT.eras)){
    const c = el(`<div class="card" data-k="${k}"><b>${v.label}</b></div>`);
    c.onclick = ()=>{ if(S.era!==k) S.engineSettings={}; S.era=k; sel(eras,c);
      // era drives everything: if the current map has no preset for it, jump
      // to the first map that does
      if (!S.map || !OPT.maps[S.map].presets[k]) {
        const valid = Object.keys(OPT.maps).find(mk=>OPT.maps[mk].presets[k]);
        S.map = valid;
        sel(document.getElementById('maps'), document.querySelector(`#maps .card[data-k="${valid}"]`));
      }
      refreshEraGating(); fillHome(); refreshDressUI(); renderCorridors(); sum(); };
    eras.appendChild(c);
  }
  initFlightMode();
  document.getElementById('veteran_wingmen').onchange = ()=>{refreshWingmen();sum();};
  refreshAircraft();
  for (const key of ['start','time_of_day','weather','density']){
    const s = document.getElementById(key);
    for (const v of OPT.enums[key]) s.appendChild(el(`<option>${v}</option>`));
  }
  document.getElementById('density').value='normal';
  document.getElementById('time_of_day').value='day';
  for (const [k,t,d,on,target] of BLOCKS){
    const box = document.getElementById(target);
    if (box) box.appendChild(el(`<label class="block"><input type="checkbox" id="${k}" ${on?'checked':''}><span><b>${t}</b><small>${d}</small></span></label>`));
  }
  // The rail now NAMES the support assets (R5) and the threat cards mirror the
  // block state (R4), so every block has to keep the summary live — previously
  // only bb_carrier/bb_pattern did, and the rail went stale.
  for (const [k] of BLOCKS){
    const cb = document.getElementById(k);
    if (cb) cb.addEventListener('change', sum);
  }
  document.getElementById('bb_carrier').addEventListener('change', ()=>{ refreshCarrierUI(); refreshCommTable(); updateRail(); });
  for (const k of ['carrier_cap','carrier_aew']) document.getElementById(k)?.addEventListener('change', ()=>refreshCommTable());
  document.getElementById('bb_pattern').addEventListener('change', ()=>{ refreshPatternUI(); sum(); });
  for (const k of ['pattern_mode','pattern_kind','pattern_count','pattern_lineup'])
    document.getElementById(k).addEventListener('change', sum);
  document.getElementById('pattern_mode').addEventListener('change', refreshPatternUI);
  refreshPatternUI();
  document.getElementById('bb_route').addEventListener('change', ()=>{ refreshTimingUI(); sum(); });
  document.getElementById('timing_anchor').addEventListener('change', ()=>{ refreshTimingUI(); sum(); });
  for (const k of ['timing_at','timing_hold_min','timing_coach','timing_package'])
    document.getElementById(k).addEventListener('change', sum);
  refreshTimingUI();
  const tp = document.getElementById('templates');
  const none = el(`<div class="card sel" data-k=""><b>Build your own</b><small>Start from scratch — you configure everything below</small></div>`);
  none.onclick = ()=>{ S.engineSettings={}; S.template=null; sel(tp,none); sum(); updateRail(); };
  tp.appendChild(none);
  for (const [k,v] of Object.entries(OPT.templates)){
    const reqs = [];
    if (v.needs_carrier) reqs.push('needs a carrier map');
    if (v.needs_acls) reqs.push('SuperCarrier for ACLS');
    if (v.maps && v.maps.length) reqs.push(v.maps.map(m=>(OPT.maps[m]?.label||m)).join('/'));
    const hint = v.recipe ? 'Presets your setup — tweak anything below' : 'Crew-ops mission (locks the jet)';
    const c = el(`<div class="card" data-k="${k}" data-eras="${(v.eras||[]).join(',')}"><b>${v.label}</b><small>${hint}${reqs.length?' · '+reqs.join(' · '):''}</small></div>`);
    c.onclick = ()=>{ applyScenarioPreset(k); sel(tp,c); };
    tp.appendChild(c);
  }
  // carrier deck configuration UI
  const cl = document.getElementById('carrier_layout');
  for (const [k,v] of Object.entries(OPT.carriers._layouts))
    cl.appendChild(el(`<option value="${k}">${v}</option>`));
  refreshCarrierUI();
  document.getElementById('carrier_hull').onchange = ()=>{ refreshDeckAircraft(); refreshAircraft(); sum(); };
  bindCarrierRecipeChanges();
  document.getElementById('coalition').onchange = ()=>{ fillHome(); refreshDressUI(); sum(); };
  document.getElementById('bb_dressing').addEventListener('change', refreshDressUI);
  document.getElementById('dress_theme').onchange = ()=>{
    onThemeChange();
    if(dressMode()==='compose') seedComposerFromTheme();   // re-seed from the picked template
    sum();
  };
  document.getElementById('dress_fill').oninput = function(){
    document.getElementById('dress_fill_label').textContent = this.value + '%'; };
  document.getElementById('composer_clear').onclick = (e)=>{
    e.preventDefault();
    document.querySelectorAll('.cmixn').forEach(i=>i.value=0);
    updateComposerBanner(); sum();
  };
  document.getElementById('composer_reset').onclick = (e)=>{
    e.preventDefault(); seedComposerFromTheme(); sum();
  };
  document.getElementById('reroll').onclick = ()=>{
    document.getElementById('seed').value = Math.floor(Math.random()*99999)+1;
    sum();
  };
  try { if (localStorage.getItem('ms_gotit')==='1') document.getElementById('whatbanner').style.display='none'; } catch(e){}
  document.getElementById('whatbanner_x').onclick = ()=>{
    document.getElementById('whatbanner').style.display='none';
    try { localStorage.setItem('ms_gotit','1'); } catch(e){}
  };
  document.getElementById('dress_aircraft_mode').onchange = function(){
    document.getElementById('dress_mode_warn').style.display =
      this.value==='parked_ai' ? '' : 'none';
    sum();
  };
  document.querySelectorAll('input[name=dmode]').forEach(rb =>
    rb.onchange = ()=>{ setDressMode(true); sum(); });
  document.getElementById('threat_intensity').oninput = function(){
    setIntensityLabel(this.value); };
  document.getElementById('threat_intensity').addEventListener('change', sum);
  document.getElementById('threat_tier').onchange = sum;
  initThreatPresets();
  ['aircraft','seed'].forEach(id=>document.getElementById(id).onchange=()=>{refreshCallsign();sum();});
  document.getElementById('seed').oninput = ()=>{refreshCallsign();sum();};
  document.getElementById('callsign').oninput = sum;
  refreshCallsign();
  renderPrivacy();
  // defaults, or prefill from a share link (?r=<code>)
  const code = new URLSearchParams(location.search).get('r');
  buildRail();
  document.getElementById('gen2').onclick = function(){ generateMission(this); };
  document.getElementById('player_arm').onchange = function(){ syncPlayerArm(); renderRailOutline(); };
  document.getElementById('player_load').onchange = function(){ renderRailOutline(); };
  document.getElementById('share2').onclick = () => document.getElementById('share').click();
  let shareError = null;
  if (code) { try { applyRecipe(decodeRecipe(code)); } catch(e){ defaultSelection(); shareError = e.message; } }
  else if (!restoreState()) { defaultSelection(); }
  updateRail();
  sum();
  renderKinds();
  syncGenbarHeight();
  const step = new URLSearchParams(location.search).get('step');
  showScreen(SCREENS.some(s=>s.key===step) ? step : 'theater');
  buildRoleTabs();
  // land on entry (two paths) — unless a share link goes straight to the builder
  // deep view links: /?v=quick|library|builder (used by the 404 page's doors);
  // a share code still outranks it and lands in the Builder as always
  const vparam = new URLSearchParams(location.search).get('v');
  NAV_READY=true;
  showView(code ? 'builder' : normalizeView(vparam), 'replace');
  if (shareError){
    const notice = document.getElementById('shareerror');
    notice.textContent = `Could not open this mission: ${shareError} The Builder shows default settings.`;
    notice.hidden = false;
  }
}
function defaultSelection(){
  // era-first: default to Modern (broadest module ownership); the era click
  // auto-selects the first valid map
  const card = document.querySelector('#eras .card[data-k="modern"]')
            || document.querySelector('#eras .card');
  card.click();
}
function applyRecipe(r){
  // Imported/shared recipes may omit defaults; normalize before touching selects.
  r = {...(typeof RECIPE_DEFAULTS === 'object' ? RECIPE_DEFAULTS : {}), ...r};
  S.engineSettings = {};
  S.template = r.template || null;
  // Restore the kind FIRST and silently: it stamps defaults, and the explicit
  // values that follow in this recipe must win over anything it set.
  if (r.mission_kind) { S.kind = r.mission_kind; }
  document.querySelector(`#eras .card[data-k="${r.era}"]`)?.click();
  document.querySelector(`#maps .card[data-k="${r.map}"]`)?.click();
  S.engineSettings = Object.fromEntries(RECIPE_ENGINE_FIELDS
    .filter(k => Object.hasOwn(r, k)).map(k => [k, r[k]]));
  document.getElementById('coalition').value = r.coalition; fillHome();
  if (r.home_airbase) document.getElementById('home').value = r.home_airbase;
  document.getElementById('aircraft').value = r.aircraft;
  document.getElementById('callsign').value = r.callsign || '';
  refreshCallsign();
  setFlightMode(r.slots);
  document.getElementById('veteran_wingmen').value = r.veteran_wingmen;
  for (const k of ['start','time_of_day','weather','density']) document.getElementById(k).value = r[k];
  document.getElementById('seed').value = r.seed;
  for (const [k] of BLOCKS) document.getElementById(k).checked = !!r[k];
  for (const k of ['pattern_mode','pattern_kind','pattern_count'])
    if (r[k] != null) document.getElementById(k).value = r[k];
  const plu = document.getElementById('pattern_lineup'); if (plu) plu.checked = !!r.pattern_lineup;
  refreshPatternUI();
  setTimingUI(r);
  refreshDressUI();
  if (r.dress_fill != null){
    document.getElementById('dress_fill').value = r.dress_fill;
    document.getElementById('dress_fill_label').textContent = r.dress_fill + '%';
  }
  for (const k of ['dress_aircraft','dress_gse','dress_infra'])
    document.getElementById(k).checked = r[k] !== false;
  if (r.dress_theme) { document.getElementById('dress_theme').value = r.dress_theme; onThemeChange(); }
  if (r.dress_aircraft_mode) document.getElementById('dress_aircraft_mode').value = r.dress_aircraft_mode;
  if (r.dress_livery_style) document.getElementById('dress_livery_style').value = r.dress_livery_style;
  if (r.ramp_heavies) document.getElementById('ramp_heavies').value = r.ramp_heavies;
  document.getElementById('player_arm').checked = r.player_arm !== false;
  if (r.player_load) document.getElementById('player_load').value = r.player_load;
  syncPlayerArm();
  document.getElementById('dress_mode_warn').style.display =
    (r.dress_aircraft_mode === 'parked_ai') ? '' : 'none';
  if (r.dress_mix && Object.keys(r.dress_mix).length){
    const rb = document.querySelector('input[name=dmode][value=compose]');
    if(rb) rb.checked = true;
    setDressMode(false);
    for (const [t,n] of Object.entries(r.dress_mix)){
      const inp = document.querySelector(`.cmixn[data-type="${t}"]`);
      if(inp) inp.value = n;
    }
    updateComposerBanner();
  }
  if (r.threat_intensity != null){
    document.getElementById('threat_intensity').value = r.threat_intensity;
    setIntensityLabel(r.threat_intensity);
  }
  if (r.threat_tier) document.getElementById('threat_tier').value = r.threat_tier;
  if (r.dress_overrides) for (const [n,v] of Object.entries(r.dress_overrides)){
    const row = document.querySelector(`.pbrow[data-base="${n}"]`);
    if (row){ row.querySelector('.pbon').checked = true;
              const fl = row.querySelector('.pbfill'); fl.value = v; fl.disabled = false;
              row.querySelector('.pbval').textContent = v==0?'empty':v+'%'; }
  }
  document.querySelectorAll('.gfxl').forEach(c =>
    c.checked = r.map_layers == null || r.map_layers.includes(c.value));
  if (Array.isArray(r.corridors)) S.corridors = r.corridors.slice();
  renderCorridors();
  setCommOverrides(r.comms, true);
  const tsel = document.querySelector(`#templates .card[data-k="${r.template||''}"]`);
  S.template = r.template || null;
  if (tsel) sel(document.getElementById('templates'), tsel);
  restoreCarrierRecipe(r);
  S.engineSettings = Object.fromEntries(RECIPE_ENGINE_FIELDS
    .filter(k => Object.hasOwn(r, k)).map(k => [k, r[k]]));
  refreshWingmen();
}
function sel(container, card){
  container.querySelectorAll('.card').forEach(c=>c.classList.remove('sel'));
  card.classList.add('sel');
  container.querySelectorAll('.card').forEach(cardState);
}
// Scenario = a preset that FILLS the wizard, then you tweak. Applied here so the
// downstream screens (flight, airfields, threats, carrier) show the scenario's
// choices ready to review — never a late override.
function presetRecipe(k, era, map){
  return effectiveScenarioPreset(OPT, k, era, map);
}
function applyScenarioPreset(k){
  const rc = Object.assign({}, OPT.recipe_defaults || RECIPE_DEFAULTS,
    presetRecipe(k, S.era, S.map), {template:k});
  applyRecipe(rc);
  renderKinds(); sum(); updateRail();
}
// Only offer scenarios that fit the chosen map + era (contextual filter). A
// scenario that stops being valid (era/map change) silently resets to "Build
// your own" rather than fighting the user's theater choice.
function filterScenarios(){
  const mapHasCarrier = S.map && OPT.maps[S.map] && OPT.maps[S.map].has_carrier;
  document.querySelectorAll('#templates .card').forEach(c=>{
    const k = c.dataset.k;
    if (!k){ c.style.display=''; return; }               // "Build your own" always shows
    const v = OPT.templates[k] || {};
    let ok = true;
    if (v.eras && v.eras.length) ok = ok && v.eras.includes(S.era);
    if (v.maps && v.maps.length)  ok = ok && v.maps.includes(S.map);
    if (v.needs_carrier)          ok = ok && !!mapHasCarrier;
    c.style.display = ok ? '' : 'none';
    if (!ok && S.template===k){
      S.template=null; c.classList.remove('sel');
      document.querySelector('#templates .card[data-k=""]').classList.add('sel');
    }
  });
}
const INTENSITY_NAMES = {1:"Minimal",2:"Light",3:"Moderate",4:"Heavy",5:"Maximum"};
function setIntensityLabel(v){
  const e = document.getElementById('threat_intensity_label');
  if (e) e.textContent = INTENSITY_NAMES[+v] || "Moderate";
}
function inEra(a){
  if(!S.era) return true;
  const w = OPT.eras[S.era].window, s = a.service;
  if(!w || !s) return true;                              // unknown service = allowed
  return s[0] <= w[1] && (s[1] === null || s[1] >= w[0]); // window overlap
}
function refreshAircraft(){
  const ac = document.getElementById('aircraft');
  const prev = ac.value;
  ac.innerHTML = '';
  let pool = OPT.aircraft.filter(inEra);
  // carrier home: only carrier-capable aircraft for the selected hull's deck class
  if (document.getElementById('home')?.value === 'CARRIER'){
    const hull = document.getElementById('carrier_hull')?.value || eraHull();
    const cls = OPT.carrier_capable.hull_class[hull];
    const allowed = OPT.carrier_capable.classes[cls] || [];
    pool = pool.filter(a=>allowed.includes(a.key));
  }
  for (const a of pool)
    ac.appendChild(el(`<option value="${a.key}">${a.upcoming?'⏳ ':''}${acDisplay(a.key,a.id)}${a.kind==='helicopter'?' (helo)':''}</option>`));
  ac.value = [...ac.options].some(o=>o.value===prev) ? prev
           : (pool.some(a=>a.key==='FA_18C_hornet') ? 'FA_18C_hornet'
              : S.era==='wwii' ? (pool.some(a=>a.key==='P_51D')?'P_51D':'') : 'F_16C_50');
  if (!ac.value && ac.options.length) ac.selectedIndex = 0;
}
function refreshCarrierUI(){
  // screen visibility is owned by showScreen()/the rail; here we only populate
  const on = document.getElementById('bb_carrier')?.checked;
  if (!on) return;
  const hs = document.getElementById('carrier_hull');
  const prev = hs.value;
  hs.innerHTML = '';
  for (const [k,v] of Object.entries(OPT.carriers)){
    if (k === '_layouts' || (S.era && !v.eras.includes(S.era))) continue;
    hs.appendChild(el(`<option value="${k}">${v.label}${v.module?` — ${v.module}`:''}</option>`));
  }
  // Default to a CATOBAR deck (full fixed-wing air wing), NOT the first option
  // in the list — in Cold War that's the V/STOL Invincible, which silently
  // collapses the jet roster to the AV-8B. eraHull() prefers a catobar hull;
  // the Invincible/Harrier is still selectable for a deliberate V/STOL mission.
  if ([...hs.options].some(o=>o.value===prev)) hs.value = prev;
  else { const def = eraHull(); if (def && [...hs.options].some(o=>o.value===def)) hs.value = def; }
  refreshDeckAircraft();
}
function restoreCarrierRecipe(r){
  // Blocks must be restored first: the hull list depends on carrier being on.
  // Explicit saved choices also win over a scenario's carrier preset.
  document.getElementById('bb_carrier').checked = !!r.bb_carrier;
  refreshCarrierUI();
  const hull = document.getElementById('carrier_hull');
  if (r.carrier_hull && [...hull.options].some(o=>o.value===r.carrier_hull))
    hull.value = r.carrier_hull;
  refreshDeckAircraft();
  const layout = document.getElementById('carrier_layout');
  if (r.carrier_layout && [...layout.options].some(o=>o.value===r.carrier_layout))
    layout.value = r.carrier_layout;
  if (Array.isArray(r.carrier_deck_aircraft))
    document.querySelectorAll('.deckac').forEach(c=>c.checked=r.carrier_deck_aircraft.includes(c.value));
  document.getElementById('carrier_equipment').checked = r.carrier_equipment !== false;
  for (const key of ['carrier_cap','carrier_aew','carrier_strike'])
    document.getElementById(key).checked = !!r[key];
  refreshAircraft();
  const aircraft = document.getElementById('aircraft');
  if ([...aircraft.options].some(o=>o.value===r.aircraft)) aircraft.value = r.aircraft;
}
function bindCarrierRecipeChanges(){
  // Deck checkboxes are rebuilt on hull changes; listen on their container.
  for (const id of ['carrier_layout','carrier_equipment','carrier_cap','carrier_aew','carrier_strike','deck_aircraft'])
    document.getElementById(id).addEventListener('change', sum);
}
function refreshTimingUI(){
  const on = !!document.getElementById('bb_route')?.checked;
  document.getElementById('timing_opts').style.display = on ? '' : 'none';
  // A takeoff anchor has no time to pick: the clock is the mission start.
  const anchor = document.getElementById('timing_anchor').value;
  document.getElementById('timing_at').disabled = (anchor === 'takeoff');
}
function setTimingUI(rc){
  if (!rc) return;
  if (rc.timing_anchor){ const e=document.getElementById('timing_anchor'); if(e) e.value=rc.timing_anchor; }
  if ('timing_at' in rc){ const e=document.getElementById('timing_at'); if(e) e.value=rc.timing_at||''; }
  if ('timing_hold_min' in rc){ const e=document.getElementById('timing_hold_min'); if(e) e.value=String(rc.timing_hold_min||0); }
  for (const k of ['timing_coach','timing_package'])
    if (k in rc){ const e=document.getElementById(k); if(e) e.checked=!!rc[k]; }
  refreshTimingUI();
}
function refreshPatternUI(){
  const on = !!document.getElementById('bb_pattern')?.checked;
  document.getElementById('pattern_opts').style.display = on ? '' : 'none';
  // Formation departures: only when the server has a verified encoding, and
  // only when something actually departs.
  const lw = document.getElementById('pattern_lineup_wrap');
  if (lw) lw.style.display = (OPT && OPT.lineup_supported
      && document.getElementById('pattern_mode').value !== 'landing') ? '' : 'none';
  // no helicopters in 1944 — the era packs have none, so don't offer the choice
  const kind = document.getElementById('pattern_kind');
  const helo = [...kind.options].find(o=>o.value==='helicopter');
  if (helo){
    helo.disabled = (S.era === 'wwii');
    if (helo.disabled && kind.value === 'helicopter') kind.value = 'fighter';
  }
}
function refreshDeckAircraft(){
  const hull = OPT.carriers[document.getElementById('carrier_hull').value];
  const da = document.getElementById('deck_aircraft');
  da.innerHTML = '';
  if (!hull) return;
  for (const ref of hull.deck_aircraft){
    const key = ref.split('.').pop();
    da.appendChild(el(`<label class="block"><input type="checkbox" class="deckac" value="${key}" checked><span><b>${key.replace(/_/g,'-')}</b><small>parked on deck</small></span></label>`));
  }
}
function refreshEraGating(){
  // landlocked maps (no carrier water): disable + uncheck the carrier block
  if (S.map){
    const hasCarrier = !!OPT.maps[S.map].has_carrier;
    const cb = document.getElementById('bb_carrier');
    const blk = cb?.closest('.block');
    if (blk){
      blk.classList.toggle('dis', !hasCarrier);
      cb.disabled = !hasCarrier;
      blk.querySelector('small').textContent = hasCarrier
        ? 'CVN + escorts on BRC, TACAN 71X / ICLS 11 / Link4 (blue, coastal maps)'
        : 'No carrier water on this map';
      if (!hasCarrier && cb.checked){ cb.checked = false; }
    }
  }
  refreshCarrierUI();
  refreshPatternUI();
  // hard era gate: roster, templates, and maps all follow the period
  refreshAircraft();
  filterScenarios();
  // era-first UX: maps gray out under the chosen era; eras themselves never gray
  document.querySelectorAll('#maps .card').forEach(c=>{
    const ok = !!OPT.maps[c.dataset.k].presets[S.era];
    c.classList.toggle('dis', !ok);
  });
}
function eraHull(){
  // default hull for the current era — prefer a CATOBAR deck (full fixed-wing
  // air wing) over a V/STOL deck (Harrier-only), so choosing the carrier does
  // not needlessly collapse the jet list to the AV-8B.
  const ents = Object.entries(OPT.carriers).filter(([k,v])=>k!=='_layouts'&&v.eras.includes(S.era));
  if(!ents.length) return null;
  const cat = ents.find(([k])=>(OPT.carrier_capable.hull_class||{})[k]==='catobar');
  return (cat||ents[0])[0];
}
function selectedMapPreset(){
  return effectiveMapPreset(OPT, S.map, S.era, S.engineSettings?.lineup);
}
function fillHome(){
  if(!S.map||!S.era) return;
  const side = document.getElementById('coalition').value;
  const p = selectedMapPreset();
  const list = side==='blue'? p.blue_airbases : p.red_airbases;
  const civ = new Set(p.civilian_airbases || []);
  const h = document.getElementById('home');
  const prev = h.value;
  h.innerHTML='';
  // land bases first so a normal runway is the DEFAULT home. The carrier is an
  // opt-in choice listed last — making it the first option silently defaulted
  // users onto the boat, which also collapsed the jet list to carrier-capable
  // only (and to the AV-8B when the era's default hull was a Harrier deck).
  list.forEach(n=>h.appendChild(el(`<option value="${n}">${n}${civ.has(n)?' — civilian':''}</option>`)));
  if (side==='blue' && OPT.maps[S.map].has_carrier && eraHull())
    h.appendChild(el(`<option value="CARRIER">⚓ The carrier (start on the boat)</option>`));
  if ([...h.options].some(o=>o.value===prev)) h.value = prev;
  else h.selectedIndex = 0;     // default to the first land base, never the carrier
  h.onchange = onHomeChange;
}
function onHomeChange(){
  const isCarrier = document.getElementById('home').value === 'CARRIER';
  const cb = document.getElementById('bb_carrier');
  if (isCarrier && !cb.checked){ cb.checked = true; refreshCarrierUI(); }
  refreshAircraft();
  sum();
}
const GFX_LAYERS = [
  ["tanker","Tanker track","Racetrack + TEXACO freq/TACAN/altitude label"],
  ["awacs","AWACS orbit","OVERLORD station behind friendly lines"],
  ["cap","Carrier CAP station","Air-wing 2-ship racetrack on the threat axis"],
  ["aew","Hawkeye AEW orbit","E-2 station covering the strike group"],
  ["carrier_box","Carrier ops box","CSG operating area + BRC arrow"],
  ["targets","Target & range rings","Amber ring + name over each strike package / practice range"],
  ["farps","FARP rings","Service radius + name at each FARP"],
  ["bullseye","Bullseye","Shared reference marker (both sides)"],
  ["threats","Threat rings (intel)","Known enemy SAM engagement rings — YOUR side's map only"],
];
function initGfxUI(){
  const c = document.getElementById('gfxlayers');
  for (const [k,label,desc] of GFX_LAYERS)
    c.appendChild(el(`<label class="block"><input type="checkbox" class="gfxl" value="${k}" checked><span><b>${label}</b><small>${desc}</small></span></label>`));
}

// ===== v1.3.0 wizard navigation =====================================
// STATE ARCHITECTURE (why state can't be lost between steps):
//   1. Single source of truth: the DOM inputs themselves. Sections are
//      never unmounted — "collapse" is CSS-only — so values survive any
//      navigation by construction.
//   2. recipe() serializes the whole DOM to one plain object; applyRecipe()
//      restores it. The same pair powers share links, so persistence and
//      sharing can never drift apart.
//   3. Autosave: every change (sum() runs on every input) writes the recipe
//      to localStorage; a refresh/crash restores it. Share-link URLs (?r=)
//      take precedence over the autosave. "Reset wizard" clears it.
// ===== section-navigation: the rail SWITCHES the single visible screen =====
// v1.45.0: eight screens became four. The old set was organized by ENGINE
// SUBSYSTEM — Airfields, Threats, Support, Map graphics — which mirrored how
// the code is factored, not how a pilot decides anything. Six of eight screens
// were toggle panels for a subsystem, and the one decision that frames all of
// them (what kind of sortie is this?) wasn't asked at all.
//
// Now: Mission (what and where) → Flight (who, from where) → Theater
// (everything the mission implies, stated in words, each block openable in
// place) → Review. Fewer screens is also fewer places for something to hide,
// and it retires the Carrier screen's appearing/disappearing act in the rail.
const SCREENS = [
  {key:"theater", num:1, label:"Mission", cols:2, steps:["sec_era","sec_kind","sec_map","sec_corridors"], val:()=>{
      if(!S.era) return null;
      let s = OPT.eras[S.era].label + (S.map? ` · ${OPT.maps[S.map].label}`:'');
      if(S.kind) s += ` · ${kindDef(S.kind).label}`;
      if(S.corridors&&S.corridors.length) s += ` · ${S.corridors.length} corridor${S.corridors.length>1?'s':''}`;
      return s; }},
  {key:"flight", num:2, label:"Flight", steps:["sec_basing","carrierstep"], val:()=>{
      const k = document.getElementById('aircraft').value;
      const h = document.getElementById('home').selectedOptions[0];
      // Mode goes ahead of the airbase: the rail truncates with an ellipsis, and
      // "4-ship" is the thing this screen now exists to confirm. The airbase is
      // the one part that can afford to be the first casualty.
      const arm = document.getElementById('player_arm');
      const ld  = document.getElementById('player_load');
      // Say the loadout only when it is NOT the shipped default: the rail is a
      // summary, and a line that always ends the same way stops being read.
      const a = !arm ? '' : (!arm.checked ? ' · unarmed'
                : (ld && ld.value !== 'standard' ? ` · ${ld.value} load` : ''));
      return k ? `${document.getElementById('coalition').value} · ${flightModeLabel()} · ${acLabel(k)}`
                 + (h ? ` · ${h.text.replace('⚓ ','')}` : '') + a : null; }},
  {key:"opposition", num:3, label:"Opposition", steps:["threatstep"],
      val:()=>threatsSummary()},
  // Airfields is its own screen, not a passenger. What parks on your ramps is a
  // real decision for anyone building a scenario, and at full width it is a
  // 620px block — it only looked unmanageable when squeezed into half a column
  // next to Support. Six screens that each fit beats four where one is a
  // filing cabinet.
  {key:"airfields", num:4, label:"Airfields", steps:["dressstep"],
      val:()=>airfieldsSummary()},
  {key:"world", num:5, label:"Support & presentation", cols:2,
      steps:["sec_support","sec_comms","gfxstep"], val:()=>supportSummary(3)},
  {key:"review", num:6, label:"Review", steps:["sec_review"], val:()=>"ready"},
];

// The blocks inside each screen, for the rail outline. Every one carries a live
// value, so the whole Builder is legible from the rail without opening
// anything — which is a stronger promise than "nothing on THIS screen is
// collapsed", and it is why the accordion could go.
const BLOCK_INFO = {
  sec_era:       {label:"Era",             val:()=>OPT&&S.era?OPT.eras[S.era].label:null},
  sec_kind:      {label:"Mission",         val:()=>S.kind?kindDef(S.kind).label:null},
  sec_map:       {label:"Map",             val:()=>OPT&&S.map?OPT.maps[S.map].label:null},
  sec_corridors: {label:"Air corridors",   val:()=>S.corridors&&S.corridors.length
                                                  ? S.corridors.join(" · ") : "open theater"},
  sec_basing:    {label:"Flight & base",   val:()=>{
      const k=document.getElementById('aircraft').value;
      const h=document.getElementById('home').selectedOptions[0];
      return k ? `${acLabel(k)}${h?" · "+h.text.replace('⚓ ',''):""}` : null; }},
  carrierstep:   {label:"Carrier deck",    val:()=>{
      const h=document.getElementById('carrier_hull').selectedOptions[0];
      return h ? h.text.split(' (')[0] : "on"; }},
  threatstep:    {label:"Threats",         val:()=>threatsSummary()},
  sec_support:   {label:"Support & extras",val:()=>supportSummary(4)},
  sec_comms:     {label:"Comm plan",       val:()=>commSummary()},
  dressstep:     {label:"Airfields",       val:()=>airfieldsSummary()},
  gfxstep:       {label:"F10 map graphics",val:()=>graphicsSummary()},
  sec_review:    {label:"Review",          val:()=>"ready to build"},
};

// Per-block summaries for screen 3. Each is the same string the rail used to
// show for that screen, so nothing was lost in the merge — it just all reads
// on one page now, in words, before anything is opened.
function threatsSummary(){
  if (!document.getElementById('bb_sams')?.checked) return "Air defenses off";
  const lab = document.getElementById('threat_intensity_label')?.textContent || '';
  const t = document.getElementById('threat_tier');
  const tl = t && t.selectedOptions[0] ? t.selectedOptions[0].text.split(' —')[0] : '';
  return `${lab} · ${tl}`;
}
function syncPlayerArm(){
  const on = document.getElementById('player_arm')?.checked;
  const sel = document.getElementById('player_load');
  if (sel) { sel.disabled = !on; sel.style.opacity = on ? '' : '.5'; }
}
function airfieldsSummary(){
  if (!document.getElementById('bb_dressing')?.checked) return "Dressing off";
  if (typeof dressMode==='function' && dressMode()==='compose'){
    const tot = Object.values(composerMix()).reduce((a,b)=>a+b,0);
    return `Composed · ${tot}/field`; }
  const t = document.getElementById('dress_theme');
  const name = t && t.selectedOptions[0] ? t.selectedOptions[0].text.replace('Auto for this map — ','') : '';
  // Say the heavy setting only when it isn't the default — the rail is a
  // summary, and a line that always ends "· Normal" teaches you to stop reading.
  const h = document.getElementById('ramp_heavies');
  const hv = h && h.value !== 'auto' ? ` · ${h.selectedOptions[0].text.split(' —')[0]} heavies` : '';
  return `${name} · ${document.getElementById('dress_fill').value}% fill${hv}`;
}
function graphicsSummary(){
  const gl = [...document.querySelectorAll('.gfxl')];
  return `${gl.filter(c=>c.checked).length} of ${gl.length} layers drawn`;
}
const ALL_STEP_IDS = [...new Set(SCREENS.flatMap(s=>s.steps))];
let CUR_SCREEN = "theater";

// Per-STEP visibility. A screen can be relevant while one of its blocks is not:
// Flight always matters, but the carrier deck only exists if you are flying off
// a carrier. Without this the deck panel showed on landlocked maps.
const STEP_COND = {
  carrierstep: () => {
    const cb = document.getElementById('bb_carrier');
    const home = document.getElementById('home');
    return !!(cb && cb.checked) &&
           !!(home && [...home.options].some(o => o.value === 'CARRIER'));
  },
};

function showScreen(key, historyMode='push'){
  const scr = SCREENS.find(s=>s.key===key);
  if(!scr) return;
  if(scr.cond && !scr.cond()) key = "theater";   // don't land on a hidden screen
  // navigating anywhere dismisses the Mission Kit panel (it's a moment, not a screen)
  const kp = document.getElementById('sec_kit');
  if (kp && kp.style.display !== 'none'){ kp.style.display='none';
    document.getElementById('screennav').style.display=''; }
  CUR_SCREEN = key;
  const show = new Set(SCREENS.find(s=>s.key===key).steps);
  ALL_STEP_IDS.forEach(id=>{ const e=document.getElementById(id);
    if(!e) return;
    const ok = show.has(id) && (!STEP_COND[id] || STEP_COND[id]());
    e.style.display = ok ? '' : 'none'; });
  // Render in the order the screen DECLARES, not the order the blocks happen
  // to sit in the markup. The four blocks screen 3 absorbed were authored as
  // separate screens years apart, so their source order is meaningless now —
  // and reading "Support" above the summary that introduces it is exactly the
  // kind of small incoherence that makes a page feel undesigned. appendChild
  // MOVES a node, so state and listeners survive.
  const _main = document.querySelector('main');
  let _cols = document.getElementById('stepcols');
  if (_main && !_cols){
    _cols = document.createElement('div'); _cols.id = 'stepcols';
    _main.insertBefore(_cols, _main.firstChild);
  }
  if (_cols){ _cols.style.display=''; _cols.classList.toggle('twocol', scr.cols === 2); }
  if (_main){
    scr.steps.forEach(id=>{ const e=document.getElementById(id); if(e) _cols.appendChild(e); });
    // ...and the wizard nav goes back to LAST. Re-appending the steps would
    // otherwise leave it stranded above them, which is how it ended up pinned
    // to the top of the screen instead of the bottom.
    const _nav = document.getElementById('screennav');
    if (_nav) _main.appendChild(_nav);
  }
  document.querySelectorAll('.rstep').forEach(r=>r.classList.toggle('active', r.dataset.key===key));
  renderRailOutline();
  window.scrollTo({top:0, behavior:'smooth'});
  if(key==="review") buildReview();
  updateScreenNav(); syncCardState();
  if(CURRENT_VIEW==='builder') writeNavigation('builder',key,historyMode);
}

function corridorsFor(){ if(!OPT||!OPT.air_corridors||!S.map||!S.era) return [];
  return (OPT.air_corridors[S.map]||[]).filter(c=>(c.eras||[]).includes(S.era)); }
function renderCorridors(){
  const box=document.getElementById('corridors'); if(!box) return;
  const list=corridorsFor(), valid=new Set(list.map(c=>c.name));
  S.corridors=(S.corridors||[]).filter(n=>valid.has(n));
  const hv=document.getElementById('hv_corridors');
  if(hv) hv.textContent = S.corridors.length? S.corridors.join(', ') : (list.length?'open theater — '+list.length+' lanes available':'—');
  // fold when nothing is selected (share links with corridors auto-unfold)
  if(!list.length){ box.innerHTML='<div class="corrempty">No curated corridors for this map &amp; era yet — open theater. Free-fly, or the Builder places threats on the base-to-base axis.</div>'; return; }
  box.innerHTML=list.map(c=>{ const on=S.corridors.includes(c.name);
    return '<div class="corrcard'+(on?' on':'')+'" role="button" tabindex="0" aria-pressed="'+(on?'true':'false')+'" onclick="toggleCorridor(\''+c.name.replace(/'/g,"\\'")+'\')">'+
      '<div class="corrname">'+c.name+'</div>'+
      '<div class="corraxis">↳ '+c.axis+'</div>'+
      '<div class="correnemy">◈ Enemy: '+c.enemy+'</div></div>'; }).join('');
}
function toggleCorridor(name){ const i=S.corridors.indexOf(name);
  if(i>=0) S.corridors.splice(i,1); else S.corridors.push(name);
  renderCorridors(); sum();
  // stay open while the user is actively picking — deselecting the last lane
  // mid-interaction must not slam the section shut under their cursor
  document.getElementById('sec_corridors').classList.remove('folded'); }

function visScreens(){ return SCREENS.filter(s => !s.cond || s.cond()); }
function screenDone(scr){
  let v=null; try{ v=scr.val(); }catch(e){}
  return !!v && !['off','none','ready','defenses off'].includes(v);
}
function updateScreenNav(){
  const vs = visScreens();
  const i = vs.findIndex(s => s.key === CUR_SCREEN);
  const back=document.getElementById('navback'), next=document.getElementById('navnext'),
        prog=document.getElementById('navprogress');
  if(!back) return;
  prog.textContent = `Step ${i+1} of ${vs.length}`;
  if(i<=0){ back.style.visibility='hidden'; }
  else { back.style.visibility=''; back.onclick=()=>showScreen(vs[i-1].key); }
  if(i>=vs.length-1){ next.style.display='none'; }   // Review is the end (Generate lives there)
  else {
    next.style.display='';
    const nx = vs[i+1];
    next.textContent = `Next: ${nx.label} →`;
    next.onclick = ()=>showScreen(nx.key);
  }
}

function buildRail(){
  const c = document.getElementById('railsteps');
  c.innerHTML = '';
  for (const scr of visScreens()){
    const r = el(`<div class="rstep" data-key="${scr.key}"><div class="dot">${scr.num}</div><div><b>${scr.label}</b><small>—</small></div></div>`);
    r.onclick = () => { if(!r.classList.contains('dim')) showScreen(scr.key); };
    c.appendChild(r);
    // one slot per screen for its sub-items; only the current screen fills it,
    // so the rail stays short enough to never need its own scrollbar
    c.appendChild(el(`<div class="rsubs" data-for="${scr.key}"></div>`));
  }
  const kagain = document.getElementById('kit_again');
  if (kagain) kagain.onclick = () => document.getElementById('railreset').click();
  document.getElementById('railreset').onclick = () => {
    try { localStorage.removeItem('ms_recipe'); } catch(e){}
    location.href = location.pathname;
  };
}

// The rail lists the blocks of the screen you are on, each with its live
// value. Two things fall out of it: you can see what a screen contains before
// you get there, and a block that is off says so rather than vanishing.
function renderRailOutline(){
  document.querySelectorAll('.rsubs').forEach(box=>{
    const key = box.dataset.for;
    if (key !== CUR_SCREEN){ box.innerHTML = ''; return; }
    const scr = SCREENS.find(s=>s.key===key);
    if (!scr){ box.innerHTML = ''; return; }
    box.innerHTML = '';
    for (const id of scr.steps){
      const info = BLOCK_INFO[id];
      const node = document.getElementById(id);
      if (!info || !node) continue;
      if (STEP_COND[id] && !STEP_COND[id]()) continue;   // not applicable here
      let v = null; try { v = info.val(); } catch(e){}
      const off = !v || ['off','none','—'].includes(String(v));
      const row = el(`<div class="rsub${off?' off':''}"><b>${info.label}</b>`
                     + `<span title="${String(v||'').replace(/"/g,'&quot;')}">${v||'—'}</span></div>`);
      row.onclick = ()=> jumpToBlock(id);
      box.appendChild(row);
    }
  });
}

// Jump to a block on the current screen and mark it briefly, so the click has
// a visible destination on a long screen.
function openPerBase(on){
  const m = document.getElementById('perbase_modal');
  if (m) m.style.display = on ? '' : 'none';
  if (on) modalOpen(m); else modalClose();
}

function jumpToBlock(id){
  const e = document.getElementById(id);
  if (!e) return;
  e.scrollIntoView({behavior:'smooth', block:'start'});
  e.classList.add('flash');
  setTimeout(()=>e.classList.remove('flash'), 900);
}

function updateRail(){
  if (!OPT) return;
  // Number by VISIBLE order, not array index — with Carrier hidden the old
  // scr.num sequence read 01..05, 07 (the review-screen bug Rob spotted).
  const ord = {}; visScreens().forEach((s,i)=>ord[s.key]=i+1);
  document.querySelectorAll('.rstep').forEach(r => {
    const scr = SCREENS.find(s=>s.key===r.dataset.key);
    const hidden = scr.cond && !scr.cond();
    r.classList.toggle('dim', !!hidden);
    let v = null; try { v = scr.val(); } catch(e){}
    r.querySelector('small').textContent = hidden ? '—' : (v || '—');
    const done = !hidden && screenDone(scr);
    r.classList.toggle('done', done);
    const dot = r.querySelector('.dot');
    dot.classList.toggle('tick', done);
    dot.textContent = done ? '✓' : (ord[scr.key] || scr.num);
  });
  renderRailOutline();
  // if the current screen just became hidden (carrier turned off), fall back
  // Carrier ops availability depends on the map, which is picked AFTER the
  // kind. Keep the cards honest, and fall back loudly rather than silently
  // building something the engine will reject.
  renderKinds();
  if (S.kind && !kindAvailable(S.kind)){
    const was = kindDef(S.kind).label;
    pickKind('open', true);
    const w = document.getElementById('kind_what');
    if (w) w.innerHTML = `<b>${was}</b> isn't available on this map or with ` +
      `this aircraft — switched back to Open tasking.`;
  }
  // re-evaluate per-step conditions on the screen we are actually on
  const _scr = SCREENS.find(s=>s.key===CUR_SCREEN);
  if (_scr) _scr.steps.forEach(id=>{ const e=document.getElementById(id);
    if (e && STEP_COND[id]) e.style.display = STEP_COND[id]() ? '' : 'none'; });
  const cur = SCREENS.find(s=>s.key===CUR_SCREEN);
  if (cur && cur.cond && !cur.cond()) showScreen('theater');
  updateScreenNav(); syncCardState();
}

function buildReview(){
  if(!OPT || !S.map || !S.era) return;
  readinessController.refresh("builder_readiness", recipe());
  // One clickable row per Builder screen (reuses each screen's live value);
  // clicking a row jumps back to that section to tweak it.
  const rows = visScreens().filter(s=>s.key!=='review').map((s,i)=>{
    let v=null; try{ v=s.val(); }catch(e){}
    // i+1, not s.num: number the rows the user can SEE, so nothing skips
    return {num:i+1, key:s.key, label:s.label, val:(v==null||v==='')?'—':v}; });
  document.getElementById('review_box').innerHTML = rows.map(r=>
    '<div class="revrow" role="button" tabindex="0" onclick="showScreen(\''+r.key+'\')" title="Edit ' + r.label + '">'+
      '<span class="revnum">'+String(r.num).padStart(2,'0')+'</span>'+
      '<span class="revkey">'+r.label+'</span>'+
      '<span class="revval">'+r.val+'</span>'+
      '<span class="revedit"><svg class="icon"><use href="#i-pencil"/></svg></span></div>').join('');
}

// --- autosave (survives refresh/crash; share links take precedence) ---


// ===== end v1.3.0 wizard navigation =================================

function refreshDressUI(){
  if(!OPT||!S.era) return;
  const side = document.getElementById('coalition').value || 'blue';
  const themes = (OPT.ramp_themes[S.era]||{})[side] || {};
  const mapDef = S.map ? ((OPT.map_theme_defaults[S.map]||{})[S.era]||{})[side] : null;
  const eraDef = Object.keys(themes)[0];
  const defKey = mapDef || null;
  const sel = document.getElementById('dress_theme');
  const prev = sel.value;
  sel.innerHTML = '';
  const autoLabel = defKey && themes[defKey] ? `Auto for this map — ${themes[defKey].label}` : 'Auto (era default)';
  sel.appendChild(el(`<option value="">${autoLabel}</option>`));
  for (const [k,t] of Object.entries(themes))
    sel.appendChild(el(`<option value="${k}">${t.label}</option>`));
  if ([...sel.options].some(o=>o.value===prev)) sel.value = prev;
  onThemeChange();
  buildPerBase();
  buildComposer();
  setDressMode(false);          // keep current mode; don't reseed on rebuild
  // hide the populate BODY (not the whole screen) when dressing is off — the
  // on/off toggle at the top of the Airfields screen stays visible.
  document.getElementById('dress_body').style.display =
    document.getElementById('bb_dressing')?.checked === false ? 'none' : '';
}
// --- Ramp Composer (v1.7.0): pick exact aircraft + counts (dress_mix) ---
function dressMode(){
  const r = document.querySelector('input[name=dmode]:checked');
  return r ? r.value : 'theme';
}
function currentThemeMix(){
  // the default composition for the currently-selected theme (player's side)
  const side = document.getElementById('coalition').value || 'blue';
  const themes = (OPT.ramp_themes[S.era]||{})[side] || {};
  let key = document.getElementById('dress_theme').value;
  if(!key){                              // '' = auto → map default, else first
    key = (((OPT.map_theme_defaults[S.map]||{})[S.era]||{})[side]) || Object.keys(themes)[0];
  }
  return (themes[key] && themes[key].mix) ? themes[key].mix : {};
}
function buildComposer(){
  const cat = OPT && OPT.static_catalog;
  if(!cat || !S.era) return;
  const cont = document.getElementById('composer_cats');
  const side = document.getElementById('coalition').value || 'blue';
  const prev = composerMix();            // preserve counts across rebuilds
  cont.innerHTML = '';
  const sections = [
    [side, side==='blue' ? 'Your coalition — Blue' : 'Your coalition — Red'],
    [side==='blue'?'red':'blue', 'Red / OPFOR & Aggressors'],
  ];
  for(const [gside, glabel] of sections){
    const anySide = Object.values(cat.types).some(t => t.side===gside && t.eras.includes(S.era));
    if(!anySide) continue;
    cont.appendChild(el(`<div style="font-size:12px;font-weight:600;color:${gside==='blue'?'#6ea8ff':'#ff8a8a'};margin:10px 0 4px">${glabel}</div>`));
    for(const c of cat.categories){
      const types = Object.entries(cat.types)
        .filter(([id,t]) => t.cat===c && t.eras.includes(S.era) && t.side===gside);
      if(!types.length) continue;
      const grp = el(`<div style="margin-bottom:7px"><div style="font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;margin-bottom:3px">${cat.category_labels[c]||c}</div></div>`);
      const wrap = el(`<div style="display:flex;flex-wrap:wrap;gap:6px"></div>`);
      for(const [id,t] of types){
        const v = prev[id]||0;
        wrap.appendChild(el(`<label style="display:flex;align-items:center;gap:5px;background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:3px 7px;font-size:12.5px"><span>${t.name}</span><input type="number" class="cmixn" data-type="${id}" min="0" max="99" value="${v}" style="width:42px"></label>`));
      }
      grp.appendChild(wrap); cont.appendChild(grp);
    }
  }
  cont.querySelectorAll('.cmixn').forEach(inp => inp.oninput = ()=>{ updateComposerBanner(); sum(); });
  updateComposerBanner();
}
function seedComposerFromTheme(){
  const seed = currentThemeMix();
  document.querySelectorAll('.cmixn').forEach(inp => {
    inp.value = seed[inp.dataset.type] || 0;
  });
  updateComposerBanner();
}
function composerMix(){
  const mix = {};
  document.querySelectorAll('.cmixn').forEach(inp => {
    const n = +inp.value||0; if(n>0) mix[inp.dataset.type] = n;
  });
  return mix;
}
function updateComposerBanner(){
  const tot = Object.values(composerMix()).reduce((a,b)=>a+b,0);
  const t = document.getElementById('composer_total'); if(t) t.textContent = tot;
}
function setDressMode(seedIfEmpty){
  const compose = dressMode()==='compose';
  // keep the theme dropdown visible in BOTH modes — in compose it's the
  // "start from template" picker; only the fill slider is theme-only.
  document.getElementById('fill_col').style.display = compose ? 'none' : '';
  document.getElementById('composer').style.display = compose ? '' : 'none';
  document.getElementById('dress_theme_label').textContent = compose
    ? 'Start from template — pick a base composition, then adjust below'
    : 'Ramp theme — who parks on YOUR fields (era-filtered)';
  if(compose && seedIfEmpty && Object.keys(composerMix()).length===0)
    seedComposerFromTheme();
}
function buildPerBase(){
  if(!OPT||!S.map||!S.era) return;
  const p = selectedMapPreset();
  const civ = new Set(p.civilian_airbases || []);
  const c = document.getElementById('perbase_rows');
  const prev = {};   // keep values across rebuilds (state never lost)
  c.querySelectorAll('.pbrow').forEach(r => {
    if (r.querySelector('.pbon').checked)
      prev[r.dataset.base] = +r.querySelector('.pbfill').value;
  });
  c.innerHTML = '';
  const side = document.getElementById('coalition').value || 'blue';
  const groups = [['Your side', side==='blue'?p.blue_airbases:p.red_airbases],
                  ['Enemy',     side==='blue'?p.red_airbases:p.blue_airbases]];
  for (const [glabel, bases] of groups){
    c.appendChild(el(`<div style="color:var(--dim);font-size:11px;letter-spacing:1px;text-transform:uppercase;margin:8px 0 4px">${glabel}</div>`));
    for (const n of bases){
      const isCiv = civ.has(n);
      const row = el(`<div class="pbrow" data-base="${n}" style="display:flex;align-items:center;gap:10px;padding:4px 0;${isCiv?'opacity:.65':''}">
        <input type="checkbox" class="pbon" style="accent-color:var(--accent)">
        <span style="flex:1;font-size:13px">${n}
          <span style="font-size:10px;border:1px solid var(--line);border-radius:8px;padding:1px 6px;margin-left:6px;color:${isCiv?'var(--amber)':'var(--green)'}">${isCiv?'CIV':'MIL'}</span></span>
        <input type="range" class="pbfill" min="0" max="100" step="5" value="45" style="width:130px" disabled>
        <span class="pbval" style="width:64px;font-size:12px;color:var(--dim)">inherit</span>
      </div>`);
      const on = row.querySelector('.pbon'), fill = row.querySelector('.pbfill'), val = row.querySelector('.pbval');
      const upd = () => { val.textContent = on.checked ? (fill.value==0?'empty':fill.value+'%') : (isCiv?'not populated':'inherit');
                          fill.disabled = !on.checked; };
      on.onchange = () => { upd(); sum(); };
      fill.oninput = () => { upd(); };
      fill.onchange = () => sum();
      if (prev[n] != null){ on.checked = true; fill.value = prev[n]; }
      upd();
      c.appendChild(row);
    }
  }
}
function perBaseOverrides(){
  const out = {};
  document.querySelectorAll('.pbrow').forEach(r => {
    if (r.querySelector('.pbon').checked)
      out[r.dataset.base] = +r.querySelector('.pbfill').value;
  });
  return out;
}
function onThemeChange(){
  const side = document.getElementById('coalition').value || 'blue';
  const themes = (OPT.ramp_themes[S.era]||{})[side] || {};
  const k = document.getElementById('dress_theme').value;
  document.getElementById('dress_theme_desc').textContent = k && themes[k] ? themes[k].desc : 'Picks the right ramp for the map — e.g. US Air Force at Nellis, no Navy paint.';
}

function sum(){
  if(!OPT) return;
  refreshWingmen();
  syncThreatPreset();
  refreshCommTable();
  updateRail(); syncCardState(); saveState();
  if(!S.map||!S.era) return;
  const r = recipe();
  document.getElementById('summary').innerHTML =
    // r.aircraft is the recipe key ("FA_18C_hornet") — fine for the payload,
    // noise in the one strip that stays on screen the whole way through.
    `<span class="pfx">Preview</span>${OPT.maps[S.map].label} · ${OPT.eras[S.era].label} · ${r.coalition} · ${acLabel(r.aircraft)||r.aircraft} from ${r.home_airbase}` +
    (S.template? ` · ${S.template}` : '') + ` · seed ${r.seed}`;
}
// ===================== QUICK FLIGHT (PRD v2 §A) =====================
// One screen, three questions, one button. Composes an ordinary Recipe from a
// hidden qf_* system template + the three picks; everything else (era, base,
// weather, comms) is derived. Any new control here must remove one — the
// spice notch is the only dial.
const QF = { type:null, ac:null, map:null, spice:'realistic', bfm:'offensive', seed:1, opened:false };
const QF_TYPES = [
  {k:'qf_tanker', ic:'fuel', t:'Tanker Time',
   s:'Air-start behind the tanker, right receiver for your jet. Plug until bored.'},
  {k:'qf_bfm', ic:'swords', t:'BFM Merge',
   s:'Three perches: offensive, defensive, high-aspect. Pick the ride below.'},
  {k:'qf_guns', ic:'flame', t:'Kill the Guns',
   s:'Airborne with the target off the nose. No SAMs — set up the wheel and hit it.'},
  {k:'qf_sam', ic:'radar', t:'Beat the SAM',
   s:'Airborne just outside the ring, RWR already talking. Stand off, notch, or go under it.'},
];
// The BFM ladder. Three perches plus the everyday neutral fight — the rung is
// a PARAMETER of the rep, not four more cards on a screen that is already too
// long. Difficulty here is GEOMETRY: same bandit, same skill, three questions.
const QF_BFM_SETUPS = [
  {k:'offensive',   t:'1 · Offensive perch',  s:"1.2 nm at his six, 30\u00b0 angle off. Convert without overshooting."},
  {k:'defensive',   t:'2 · Defensive perch',  s:"He is 1.2 nm astern and slightly high. Deny the shot, force the overshoot."},
  {k:'high_aspect', t:'3 · High-aspect merge',s:"5 nm, nose to nose. Choose one-circle or two \u2014 and mean it."},
  {k:'neutral',     t:'Neutral fight',        s:"2 nm abeam. No lesson, just a fight."},
];
const QF_SPICE = [
  {k:'calm', t:'Calm', s:'Minimal opposition. Learn the mechanics.'},
  {k:'realistic', t:'Realistic', s:'The template\'s intended balance.'},
  {k:'hostile', t:'Hostile', s:'Dense, sharp, unfair. Bring your A-game.'},
];

function qfOpen(){
  if(!OPT) return;
  if(!QF.opened){
    QF.opened = true; QF.seed = 1 + Math.floor(Math.random()*99999);
    fetch('/api/ev',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({event:'qf_open'})}).catch(()=>{});
  }
  qfRender();
}

function qfTplEras(k){ return (OPT.templates[k]||{}).eras||[]; }

function qfMapsFor(type){
  // a map qualifies if it shares at least one era with the mission type
  const te = new Set(qfTplEras(type));
  const allowed = (OPT.templates[type]||{}).maps;
  return Object.keys(OPT.maps).filter(mk =>
    (!allowed || !allowed.length || allowed.includes(mk)) &&
    Object.keys(OPT.maps[mk].presets).some(e=>te.has(e)));
}

function qfAcList(type){
  const own = ownedAc();
  let list = (OPT.aircraft||[]).filter(a=>!a.upcoming);
  if (type==='qf_tanker') list = list.filter(a=>a.can_refuel);
  if (type==='qf_bfm') list = list.filter(a=>a.kind==='plane');
  if (own) {
    const owned = list.filter(a=>own.has(a.key));
    if (owned.length) return {list: owned, owned:true};
  }
  return {list, owned:false};
}

function qfEra(type, mapK, acKey){
  // derive the era: type ∩ map, preferring modern > coldwar > wwii, biased to
  // the aircraft's service window when known
  const te = new Set(qfTplEras(type));
  if (!qfMapsFor(type).includes(mapK)) return null;
  const aircraft = (OPT.aircraft||[]).find(a=>a.key===acKey && !a.upcoming);
  if (!aircraft || (type==='qf_tanker' && !aircraft.can_refuel) ||
      (type==='qf_bfm' && aircraft.kind!=='plane')) return null;
  const me = Object.keys(OPT.maps[mapK].presets);
  // Preference order first, then anything else the data offers — a hard-coded
  // three-element list meant Quick Flight could never reach a new era.
  const PREF = ['modern','gwot','coldwar','wwii'];
  const order = PREF.concat(Object.keys(OPT.eras||{}).filter(e=>!PREF.includes(e)));
  const cands = order.filter(e=>te.has(e)&&me.includes(e));
  if(!cands.length) return null;
  const svc = ((OPT.aircraft||[]).find(a=>a.key===acKey)||{}).service;
  if (svc){
    const [from,to] = svc;
    for (const e of cands){
      const w = (OPT.eras[e]||{}).window;
      if (!w) return e;
      if ((to==null || to>=w[0]) && from<=w[1]) return e;
    }
    return null;
  }
  return cands[0];
}

function qfRender(){
  const own = ownedMaps();
  document.getElementById('qf_types').innerHTML = QF_TYPES.map(t=>
    `<div class="qcard${QF.type===t.k?' sel':''}" role="button" tabindex="0" aria-pressed="${QF.type===t.k}" onclick="qfPick('type','${t.k}')">`+
    `<span class="qi"><svg class="icon lg"><use href="#i-${t.ic}"/></svg></span><b>${t.t}</b><small>${t.s}</small></div>`).join('');
  const {list, owned} = qfAcList(QF.type||'qf_bfm');
  if (QF.ac && !list.some(a=>a.key===QF.ac)) QF.ac = null;
  document.getElementById('qf_acs').innerHTML = list.map(a=>
    `<div class="qcard${QF.ac===a.key?' sel':''}" role="button" tabindex="0" aria-pressed="${QF.ac===a.key}" onclick="qfPick('ac','${a.key}')">`+
    `<b>${acDisplay(a.key, a.id)}</b></div>`).join('') +
    (owned?'':'<div class="qcard dis"><small>Tip: set “My DCS content” in the Library to trim this to what you own.</small></div>');
  const maps = qfMapsFor(QF.type||'qf_bfm');
  if (QF.map && !maps.includes(QF.map)) QF.map = null;
  const sorted = maps.sort((a,b)=>(OPT.maps[b].free-OPT.maps[a].free)||a.localeCompare(b));
  document.getElementById('qf_maps').innerHTML = sorted.map(mk=>{
    const un = own && !own.has(mk);
    return `<div class="qcard${QF.map===mk?' sel':''}${un?' dis':''}" role="button" tabindex="${un?-1:0}" aria-disabled="${!!un}" aria-pressed="${QF.map===mk}" onclick="qfPick('map','${mk}')">`+
      `<b>${OPT.maps[mk].label}</b><small>${OPT.maps[mk].free?'Free terrain':'Paid terrain'}</small></div>`;}).join('');
  // the ladder appears only for the ride it belongs to
  const isBfm = QF.type === 'qf_bfm';
  document.getElementById('qf_setup_wrap').style.display = isBfm ? '' : 'none';
  if (isBfm) document.getElementById('qf_setup').innerHTML = QF_BFM_SETUPS.map(b=>
    `<div class="qcard${QF.bfm===b.k?' sel':''}" role="button" tabindex="0" aria-pressed="${QF.bfm===b.k}" onclick="qfPick('bfm','${b.k}')">`+
    `<b>${b.t}</b><small>${b.s}</small></div>`).join('');
  document.getElementById('qf_spice').innerHTML = QF_SPICE.map(s=>
    `<div class="qcard${QF.spice===s.k?' sel':''}" role="button" tabindex="0" aria-pressed="${QF.spice===s.k}" onclick="qfPick('spice','${s.k}')">`+
    `<b>${s.t}</b><small>${s.s}</small></div>`).join('');
  const ready = QF.type && QF.ac && QF.map;
  const era = ready ? qfEra(QF.type, QF.map, QF.ac) : null;
  document.getElementById('qf_fly').disabled = GENERATING || !era;
  if(era) readinessController.refresh('quick_readiness', qfRecipe());
  else readinessController.clear('quick_readiness');
  document.getElementById('qf_hint').textContent = ready
    ? (era ? `${OPT.eras[era].label} · seed ${QF.seed} — era, base, weather and comms are set for you.`
           : 'That jet, mission and map have no era in common — pick another map.')
    : 'Pick a mission, a jet and a map.';
}

function qfPick(what, v){
  if (what==='map' && (!qfMapsFor(QF.type||'qf_bfm').includes(v) ||
      (ownedMaps() && !ownedMaps().has(v)))) return;
  if (what==='ac' && !qfAcList(QF.type||'qf_bfm').list.some(a=>a.key===v)) return;
  // spice and the BFM rung always have a value — deselecting them would leave
  // the ride undefined, which is not a state a pilot can fly
  QF[what] = (QF[what]===v && what!=='spice' && what!=='bfm') ? null : v;
  qfRender();
}

function qfRecipe(){
  const tpl = OPT.templates[QF.type] || {};
  const rc = presetRecipe(QF.type, qfEra(QF.type, QF.map, QF.ac), QF.map);
  rc.template = QF.type;
  rc.aircraft = QF.ac;
  rc.map = QF.map;
  rc.era = qfEra(QF.type, QF.map, QF.ac);
  rc.coalition = 'blue';
  rc.slots = 1;
  rc.seed = QF.seed;
  if (QF.type === 'qf_bfm') rc.bfm_setup = QF.bfm;
  if (QF.spice==='calm')    rc.threat_intensity = 1;
  if (QF.spice==='hostile') rc.threat_intensity = 4;
  return rc;
}

document.getElementById('qf_die').onclick = ()=>{
  QF.seed = 1 + Math.floor(Math.random()*99999);
  fetch('/api/ev',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({event:'qf_reroll'})}).catch(()=>{});
  ga('qf_reroll');
  qfRender();
};

document.getElementById('qf_fly').onclick = async ()=>{
  const rc = qfRecipe();
  if (!rc.era) return;
  await generateMission(document.getElementById('qf_fly'), {source:'quick', rc});
};

document.getElementById('perbase_open').onclick = ()=> openPerBase(true);
document.getElementById('perbase_close').onclick = ()=> openPerBase(false);
document.getElementById('perbase_modal').addEventListener('click', e=>{
  if (e.target.id === 'perbase_modal') openPerBase(false); });

document.getElementById('brief').onclick = function(){
  const kitVisible=document.getElementById('sec_kit').style.display!=='none';
  downloadBrief(this,kitVisible ? MISSION_RESULTS.builder : null);
};
document.getElementById('share').onclick = async ()=>{
  const code = encodeRecipe(recipe());
  const url = `${location.origin}/?r=${code}`;
  await navigator.clipboard.writeText(url);
  document.getElementById('status').textContent = 'Share link copied — anyone can regenerate this exact starter.';
};

function normalizeView(v){
  if(v==='train') return 'pipeline';
  return ['quick','library','builder','pipeline','entry'].includes(v) ? v : 'entry';
}
function writeNavigation(v, screen, mode='push'){
  if(!NAV_READY || mode==='none') return;
  const url=new URL(location.href);
  if(v==='entry') url.searchParams.delete('v'); else url.searchParams.set('v',v);
  if(v==='builder') url.searchParams.set('step',screen); else url.searchParams.delete('step');
  if(url.href===location.href && mode!=='replace') return;
  history[mode==='replace'?'replaceState':'pushState']({view:v,screen},'',url);
}
function showView(v, historyMode='push'){
  v=normalizeView(v); CURRENT_VIEW=v;
  writeNavigation(v,CUR_SCREEN,historyMode);
  const build=v==='builder';
  const shareNotice = document.getElementById('shareerror');
  shareNotice.hidden = !build || !shareNotice.textContent;
  // GA4's automatic page_view fires once, on load. This app never navigates
  // again — the three doors are the same document — so without this the whole
  // Library and Fly Now are invisible in the reports.
  ga('view_change', {view: v});
  document.getElementById('entry').classList.toggle('on',v==='entry');
  document.getElementById('library').classList.toggle('on',v==='library');
  document.getElementById('quick').classList.toggle('on',v==='quick');
  document.getElementById('pipeline').classList.toggle('on',v==='pipeline');
  let dismissed=false; try{dismissed=localStorage.getItem('ms_gotit')==='1';}catch(e){}
  document.getElementById('whatbanner').style.display=(build&&!dismissed)?'':'none';
  document.querySelector('.app').style.display=build?'':'none';
  document.querySelector('.genbar').style.display=build?'':'none';
  // light the active view tab; entry lights neither (choice not yet made)
  document.querySelectorAll('#viewtabs button').forEach(b=>{
    const on = b.dataset.v===v;
    b.classList.toggle('on', on);
    if (on) b.setAttribute('aria-current','page'); else b.removeAttribute('aria-current');
  });
  // the tab title should say where you are — it was frozen on one string,
  // so browser history and pinned tabs were unreadable
  document.title = ({quick:'Fly Now', library:'Mission Library', builder:'Builder',
                     pipeline:'Training Pipeline', entry:'DCS Sortie Starter'}[v] || 'DCS Sortie Starter')
                   + (v==='entry' ? '' : ' · DCS Sortie Starter');
  if(v==='library') renderLib();
  if(v==='quick') qfOpen();
  if(v==='pipeline') renderPipeline();
  window.scrollTo(0,0);
}

// ---- Modal accessibility (WCAG 2.1.2 / 4.1.2): focus trap, Escape, restore.
// One trap for all three dialogs; openers call modalOpen(container), closers
// modalClose(). Focus returns to whatever had it before the dialog opened.
let _modalPrev=null,_modalEl=null;
const _FOCUSABLE='button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])';
function modalOpen(el){
  _modalPrev=document.activeElement; _modalEl=el;
  const f=el.querySelector(_FOCUSABLE); (f||el).focus();
}
function modalClose(){
  _modalEl=null;
  if(_modalPrev&&_modalPrev.focus){_modalPrev.focus();} _modalPrev=null;
}
document.addEventListener('keydown',e=>{
  if(!_modalEl) return;
  if(e.key==='Escape'){
    if(_modalEl.id==='ownmodal'||_modalEl.querySelector('#ocardinner')) closeOwn();
    else if(_modalEl.id==='perbase_modal') openPerBase(false);
    else if(_modalEl.id==='contactmodal') closeContact();
    else closeDetail();
    e.stopPropagation(); return;
  }
  if(e.key!=='Tab') return;
  const f=[..._modalEl.querySelectorAll(_FOCUSABLE)].filter(x=>x.offsetParent!==null);
  if(!f.length) return;
  const first=f[0],last=f[f.length-1];
  if(e.shiftKey&&document.activeElement===first){last.focus();e.preventDefault();}
  else if(!e.shiftKey&&document.activeElement===last){first.focus();e.preventDefault();}
});

// ---- Keyboard activation (WCAG 2.1.1): Enter/Space operate every element
// carrying role=button/switch/checkbox — the JS-rendered cards, chips and
// toggles. Native <button>s already do this; the delegate skips them.
document.addEventListener('keydown',e=>{
  if(e.key!=='Enter'&&e.key!==' ')return;
  const t=e.target;
  if(!t||t.tagName==='BUTTON'||t.tagName==='A'||t.tagName==='INPUT'||t.tagName==='SELECT'||t.tagName==='TEXTAREA')return;
  const r=t.getAttribute&&t.getAttribute('role');
  if(r==='button'||r==='switch'||r==='checkbox'){
    e.preventDefault(); if(t.getAttribute('aria-disabled')!=='true' && !t.classList.contains('dis')) t.click();
  }
});

window.addEventListener('popstate',()=>{
  if(!OPT) return;
  const params=new URLSearchParams(location.search), view=normalizeView(params.get('v'));
  if(view==='builder') showScreen(params.get('step')||'theater','none');
  showView(view,'none');
});

// ===================== CONTACT =====================
// The only way a pilot can talk back to us. Design notes in
// docs/contact-form-spec.md; the two that matter here:
//   * email is OPTIONAL — requiring it costs us the anonymous bug reports,
//     which are the most useful messages we get;
//   * a failed send NEVER clears the textarea. Someone spent five minutes
//     writing that.
let _cToken = null;
function openContact(){
  ga('contact_open');
  const m = document.getElementById('contactmodal');
  m.classList.add('on');
  // fresh token per open: it carries the issue time the server checks against
  fetch('/api/contact/token').then(r=>r.json()).then(t=>{
    _cToken = t;
    const sel = document.getElementById('c_topic');
    if (sel.options.length <= 1)
      (t.topics||[]).forEach(o=>{ const e=document.createElement('option');
        e.value=o.value; e.textContent=o.label; sel.appendChild(e); });
  }).catch(()=>{ _cToken = null; });
  document.getElementById('c_ctx_body').textContent = contactContext(true);
  cCount();
  modalOpen(m);
}
function closeContact(){
  document.getElementById('contactmodal').classList.remove('on');
  modalClose();
}
// Disclosed, not silent (spec §2.3): a bug report without a version is half a
// report, so we attach one — and show the user exactly what that means.
function contactContext(asText){
  const view = ['quick','library','builder'].find(v=>{
    const e=document.getElementById(v); return e && e.classList.contains('on'); }) || 'home';
  // The mission CONFIGURATION, not the person. Prefer the last thing they
  // actually generated; fall back to the live Builder state. Named `rc` so it
  // cannot shadow the global recipe() it calls.
  let rc = null;
  try {
    const r = (typeof LAST_GEN_RECIPE !== 'undefined' && LAST_GEN_RECIPE)
      ? LAST_GEN_RECIPE
      : (view === 'builder' && typeof recipe === 'function' ? recipe() : null);
    if (r) rc = JSON.stringify(r).slice(0, 400);
  } catch (e) { rc = null; }
  if (asText) return 'The app version and which screen you were on (' + view + ')'
    + (rc ? ', plus the mission settings you have set up, so we can reproduce it.' : '.')
    + ' Nothing about you personally.';
  return {view: view, recipe: rc};
}
function cCount(){
  const t=document.getElementById('c_comment'), c=document.getElementById('c_count');
  const max=(_cToken&&_cToken.max_comment)||4000, n=t.value.length;
  c.textContent = n > max-500 ? (max-n)+' characters left' : '';
}
function cErr(field,msg){
  const i=document.getElementById('c_'+field), e=document.getElementById('c_'+field+'_err');
  if(i) i.classList.toggle('bad', !!msg);
  if(e) e.textContent = msg||'';
}
// Client-side validation mirrors the server's rules. Not a substitute for it
// (never trust the client) — it is there so a typo costs no round trip, and so
// an obviously-empty form never reaches the anti-bot layer, which would silently
// swallow it. Returns true when the form is worth sending.
function cValidate(p){
  let ok = true;
  const fail = (f,m) => { cErr(f,m); ok = false; };
  if(!p.name.trim()) fail('name','Please tell us your name.');
  if(!p.topic) fail('topic',"Please choose what this is about.");
  if(p.comment.trim().length < 10) fail('comment','Please write at least 10 characters.');
  const e = p.email.trim();
  if(e && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) fail('email',"That email address doesn't look right.");
  if(!ok){
    const first = document.querySelector('#cform .bad');
    if(first) first.focus();
  }
  return ok;
}
function submitContact(ev){
  ev.preventDefault();
  ['name','email','topic','comment'].forEach(f=>cErr(f,''));
  const btn=document.getElementById('c_send'), st=document.getElementById('c_status');
  const payload={
    name: document.getElementById('c_name').value,
    email: document.getElementById('c_email').value,
    topic: document.getElementById('c_topic').value,
    comment: document.getElementById('c_comment').value,
    website: document.getElementById('c_website').value,
    context: contactContext(false),
    issued: _cToken?_cToken.issued:0, sig: _cToken?_cToken.sig:''
  };
  if(!cValidate(payload)){ st.textContent=''; return; }
  btn.disabled=true; st.textContent='Sending…';
  // The server rejects submissions completed faster than a human could type
  // (a bot filter) by silently discarding them. A genuinely quick human — or
  // someone pasting a prepared message — must never lose their words to that,
  // so OUR client simply never violates the floor: it waits out the remainder.
  const MINMS = 3200;
  const waited = _cToken ? (Date.now()/1000 - _cToken.issued) * 1000 : MINMS;
  const hold = Math.max(0, MINMS - waited);
  new Promise(r=>setTimeout(r, hold)).then(()=>
  fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},
                        body:JSON.stringify(payload)}))
    .then(async r=>{
      const d = await r.json().catch(()=>({}));
      if(r.ok){ contactDone(); return; }
      btn.disabled=false;
      if(r.status===422 && d.errors){
        st.textContent='';
        Object.keys(d.errors).forEach(f=>cErr(f,d.errors[f]));
        const first=document.getElementById('c_'+Object.keys(d.errors)[0]);
        if(first) first.focus();
      } else {
        st.textContent = (d && d.detail) ? d.detail : 'That didn\'t send. Please try again.';
      }
    })
    .catch(()=>{ btn.disabled=false;
      st.textContent='That didn\'t send — check your connection and try again.'; });
}
function contactDone(){
  const card=document.getElementById('ccardinner');
  card.innerHTML='<button class="dclose" onclick="closeContact()" aria-label="Close">×</button>'
    +'<div class="eyebrow" style="margin-bottom:6px">Sent</div>'
    +'<h2 style="margin:0 0 4px;font-size:24px">Thank you — that\'s in.</h2>'
    +'<p class="dprem" style="font-size:13.5px">We read everything that comes through here. '
    +'If you left an email, we\'ll reply when there\'s something worth saying.</p>'
    +'<div class="dcta"><button class="prime" onclick="closeContact()">Close</button></div>';
  card.querySelector('.prime').focus();
}
// Clear a field's error the moment the user starts fixing it — leaving a red
// "please tell us your name" under a filled-in name field is the form telling
// someone they're still wrong when they aren't.
document.addEventListener('input', e=>{
  const id = e.target && e.target.id;
  if(!id || id.indexOf('c_') !== 0) return;
  if(id === 'c_comment') cCount();
  const f = id.slice(2);
  if(['name','email','topic','comment'].indexOf(f) >= 0) cErr(f, '');
});
document.addEventListener('change', e=>{
  if(e.target && e.target.id === 'c_topic') cErr('topic', '');
});

Object.assign(window, createCommController({state:S,getOptions:()=>OPT,callbacks:{sel: (...args) => sel(...args), updateRail: (...args) => updateRail(...args), recipe: (...args) => recipe(...args), saveState: (...args) => saveState(...args) , SUP_NAMES},environment:{document,window,localStorage,fetch,navigator,location,history,prompt}}));

Object.assign(window, createLibraryController({state:S,getOptions:()=>OPT,callbacks:{refreshReadiness:(...args)=>readinessController.refresh(...args),acCleanId: (...args) => acCleanId(...args), acDisplay: (...args) => acDisplay(...args), applyScenarioPreset: (...args) => applyScenarioPreset(...args), ga: (...args) => ga(...args), modalClose: (...args) => modalClose(...args), modalOpen: (...args) => modalOpen(...args), refreshAircraft: (...args) => refreshAircraft(...args), showScreen: (...args) => showScreen(...args), showView: (...args) => showView(...args), sum: (...args) => sum(...args), track: (...args) => track(...args), updateRail: (...args) => updateRail(...args), recipe: (...args) => recipe(...args) , AC_NAME},environment:{document,window,localStorage,fetch,navigator,location,history,prompt}}));

Object.assign(window, createRecipeController({state:S,getOptions:()=>OPT,callbacks:{applyRecipe: (...args) => applyRecipe(...args), composerMix: (...args) => composerMix(...args), dressMode: (...args) => dressMode(...args), perBaseOverrides: (...args) => perBaseOverrides(...args), commOverrides: (...args) => commOverrides(...args) , BLOCKS, RECIPE_DEFAULTS, RECIPE_ENGINE_FIELDS},environment:{document,window,localStorage,fetch,navigator,location,history,prompt}}));


const missionResultsController = createMissionResults({
  getOptions:()=>OPT,
  callbacks:{esc:(...args)=>esc(...args),recipe:(...args)=>recipe(...args),visitorId,ga,
             showScreen,qfEra,QF,ALL_STEP_IDS},
  environment:{document,fetch,URL}
});
Object.assign(window, missionResultsController.functions);
Object.defineProperties(window, {
  LAST_GEN_RECIPE:{get:()=>missionResultsController.lastRecipe},
  GENERATING:{get:()=>missionResultsController.busy},
  MISSION_RESULTS:{get:()=>missionResultsController.results}
});
const readinessController = createReadinessController({document,fetch,ownedMaps,ownedAc,ownedModules,esc});
init();
