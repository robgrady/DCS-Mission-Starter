/** createRecipeController: explicit state, environment and cross-controller actions. */
function createRecipeController({state, getOptions, callbacks, environment}) {
const {document, window, localStorage, fetch, navigator, location, history, prompt} = environment;
const S = state;
const OPT = new Proxy({}, {get: (_, key) => getOptions()?.[key]});
const { BLOCKS, RECIPE_DEFAULTS, RECIPE_ENGINE_FIELDS, applyRecipe, composerMix, dressMode, perBaseOverrides, commOverrides } = callbacks;
function encodeRecipe(r){
  const diff = {};
  for (const [k,v] of Object.entries(r)) if (JSON.stringify(RECIPE_DEFAULTS[k])!==JSON.stringify(v)) diff[k]=v;
  const bytes = new TextEncoder().encode(JSON.stringify({v:1, r:diff}));
  return btoa(Array.from(bytes, b => String.fromCharCode(b)).join('')).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}

function decodeRecipe(code){
  const b = code.replace(/-/g,'+').replace(/_/g,'/');
  const bytes = Uint8Array.from(atob(b), c => c.charCodeAt(0));
  let obj;
  try { obj = JSON.parse(new TextDecoder('utf-8', {fatal:true}).decode(bytes)); }
  catch(e){
    // The old browser codec used btoa directly, so accented Latin-1 names
    // could be saved without UTF-8. Accept that only for legacy bare recipes.
    obj = JSON.parse(atob(b));
    if (obj && typeof obj === 'object' && ('v' in obj || 'r' in obj)) throw e;
  }
  if (!obj || typeof obj !== 'object' || Array.isArray(obj)) throw new Error('Invalid share link.');
  let diff = obj;
  if ('v' in obj || 'r' in obj){
    if (!Number.isInteger(obj.v) || obj.v < 1 || !('r' in obj)) throw new Error('Invalid share link version.');
    if (obj.v > 1) throw new Error('This link needs a newer version of Sortie Starter.');
    diff = obj.r;
  }
  if (!diff || typeof diff !== 'object' || Array.isArray(diff)) throw new Error('Invalid share link settings.');
  for (const k of Object.keys(diff)) if (!Object.hasOwn(RECIPE_DEFAULTS, k) && k !== 'corridors' && !RECIPE_ENGINE_FIELDS.includes(k)) throw new Error(`Unknown mission setting: ${k}.`);
  return {...RECIPE_DEFAULTS, ...diff};
}

function saveState(){
  try { localStorage.setItem('ms_recipe', JSON.stringify(recipe())); } catch(e){}
}

function restoreState(){
  try {
    const raw = localStorage.getItem('ms_recipe');
    if (!raw) return false;
    applyRecipe(JSON.parse(raw));
    return true;
  } catch(e){ return false; }
}

function recipe(){
  const r = {
    ...(S.engineSettings || {}),
    map:S.map, era:S.era, template:S.template,
    crew_difficulty:(document.getElementById('crew_difficulty')||{}).value||'qualified',
    coalition:document.getElementById('coalition').value,
    aircraft:document.getElementById('aircraft').value,
    callsign:(document.getElementById('callsign')?.value||'').trim()||null,
    home_airbase:document.getElementById('home').value,
    slots:+document.getElementById('slots').value,
    start:document.getElementById('start').value,
    time_of_day:document.getElementById('time_of_day').value,
    weather:document.getElementById('weather').value,
    density:document.getElementById('density').value,
    seed:+document.getElementById('seed').value,
    mission_kind: S.kind || 'open',
  };
  for (const [k] of BLOCKS) r[k]=document.getElementById(k).checked;
  r.threat_intensity = +document.getElementById('threat_intensity').value;
  r.threat_tier = document.getElementById('threat_tier').value;
  if (r.bb_pattern){
    r.pattern_mode = document.getElementById('pattern_mode').value;
    r.pattern_kind = document.getElementById('pattern_kind').value;
    r.pattern_count = +document.getElementById('pattern_count').value;
    r.pattern_lineup = !!(OPT && OPT.lineup_supported) && r.pattern_mode !== 'landing'
                       && !!document.getElementById('pattern_lineup')?.checked;
  }
  if (r.bb_route){
    r.timing_anchor = document.getElementById('timing_anchor').value;
    const at = document.getElementById('timing_at').value;
    // HH:MM:SS from the picker; the server accepts either. A takeoff
    // anchor has no time — sending one is a 422, not a preference.
    r.timing_at = (r.timing_anchor !== 'takeoff' && at) ? at : null;
    r.timing_hold_min = +document.getElementById('timing_hold_min').value;
    r.timing_coach = document.getElementById('timing_coach').checked;
    r.timing_package = document.getElementById('timing_package').checked;
  }
  if (r.bb_dressing){
    const fill = +document.getElementById('dress_fill').value;
    if (fill !== 45) r.dress_fill = fill;
    r.dress_aircraft = document.getElementById('dress_aircraft').checked;
    r.dress_gse = document.getElementById('dress_gse').checked;
    r.dress_infra = document.getElementById('dress_infra').checked;
    r.dress_theme = document.getElementById('dress_theme').value || null;
    r.dress_aircraft_mode = document.getElementById('dress_aircraft_mode').value;
    r.dress_livery_style = document.getElementById('dress_livery_style').value;
    r.ramp_heavies = document.getElementById('ramp_heavies').value;
    r.player_arm = document.getElementById('player_arm').checked;
    r.player_load = document.getElementById('player_load').value;
    const ov = perBaseOverrides();
    if (Object.keys(ov).length) r.dress_overrides = ov;
    if (dressMode()==='compose'){
      const cmix = composerMix();
      if (Object.keys(cmix).length) r.dress_mix = cmix;
    }
  }
  const gl = [...document.querySelectorAll('.gfxl')];
  const on = gl.filter(c=>c.checked).map(c=>c.value);
  r.map_layers = on.length === gl.length ? null : on;   // null = auto/all
  if (r.bb_carrier){
    r.carrier_hull = document.getElementById('carrier_hull').value || null;
    r.carrier_layout = document.getElementById('carrier_layout').value;
    r.carrier_deck_aircraft = [...document.querySelectorAll('.deckac:checked')].map(c=>c.value);
    r.carrier_equipment = document.getElementById('carrier_equipment').checked;
    r.carrier_cap = document.getElementById('carrier_cap').checked;
    r.carrier_aew = document.getElementById('carrier_aew').checked;
    r.carrier_strike = document.getElementById('carrier_strike').checked;
  }
  r.corridors = (S.corridors||[]).slice();
  r.comms = commOverrides();
  return r;
}
return { decodeRecipe, encodeRecipe, recipe, restoreState, saveState };
}
