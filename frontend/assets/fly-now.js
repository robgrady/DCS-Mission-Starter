/* Fly Now keeps the last valid recipe choices and aircraft history on this browser. */
function createFlyNowControls({
  state, getOptions, qfAcList, qfMapsFor, qfEra, ownedMaps, ownedAc, acDisplay, pick, render, openOwn,
}) {
  const storageKey = 'ss_fly_now_v1';
  const historyLimit = 4;
  const search = document.getElementById('qf_aircraft_search');
  const picker = document.getElementById('qf_aircraft');
  const pickerStatus = document.getElementById('qf_aircraft_status');
  const summary = document.getElementById('qf_selection');
  let recent = [];
  let displayed = [];
  let scope = '';

  function readHistory() {
    try {
      return JSON.parse(localStorage.getItem(storageKey)) || {};
    } catch {
      return {};
    }
  }

  function mapOptions(type) {
    const maps = qfMapsFor(type);
    const owned = ownedMaps();
    return owned ? maps.filter(map => owned.has(map)) : maps;
  }

  function aircraftOptions(type, maps) {
    const compatible = qfAcList(type, false).list.filter(aircraft =>
      maps.some(map => qfEra(type, map, aircraft.key)));
    const owned = ownedAc();
    if (!owned) return { aircraft: compatible, scope: '' };
    const inLibrary = compatible.filter(aircraft => owned.has(aircraft.key));
    return inLibrary.length
      ? { aircraft: inLibrary, scope: 'Showing aircraft from My DCS content.' }
      : { aircraft: compatible, scope: 'No owned aircraft match. Showing all compatible aircraft.' };
  }

  function recoverSetup(types, bfm, spice) {
    const stored = readHistory();
    if (Array.isArray(stored.recent)) {
      recent = [...new Set(stored.recent.filter(key => typeof key === 'string'))].slice(0, historyLimit);
    }
    const setup = stored.setup;
    if (!setup || !types.some(type => type.k === setup.type) ||
        !mapOptions(setup.type).includes(setup.map) ||
        !aircraftOptions(setup.type, [setup.map]).aircraft.some(aircraft => aircraft.key === setup.ac)) return;
    const {type, ac, map, seed} = setup;
    Object.assign(state, {type, ac, map});
    if (bfm.some(option => option.k === setup.bfm)) state.bfm = setup.bfm;
    if (spice.some(option => option.k === setup.spice)) state.spice = setup.spice;
    if (Number.isInteger(seed) && seed >= 1 && seed <= 99999) state.seed = seed;
  }

  function searchable(value) {
    return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  }

  function filterOptions() {
    const words = search.value.trim().split(/\s+/).map(searchable).filter(Boolean);
    const matches = displayed.filter(aircraft => {
      const terms = [aircraft.label, aircraft.key, aircraft.id].map(searchable);
      return words.every(word => terms.some(term => term.includes(word)));
    });
    const byKey = new Map(matches.map(aircraft => [aircraft.key, aircraft]));
    const recentMatches = recent.map(key => byKey.get(key)).filter(Boolean);
    const otherMatches = matches.filter(aircraft => !recent.includes(aircraft.key));
    const shownSelection = matches.some(option => option.key === state.ac);
    const selected = !shownSelection && state.ac
      ? getOptions().aircraft.find(aircraft => aircraft.key === state.ac)
      : null;
    const placeholder = selected
      ? 'Selected: ' + acDisplay(selected.key, selected.id)
      : 'Choose an aircraft';
    picker.replaceChildren(new Option(placeholder, ''));
    function addGroup(label, options) {
      if (!options.length) return;
      const group = document.createElement('optgroup');
      group.label = label;
      group.append(...options.map(option => new Option(option.label, option.key)));
      picker.append(group);
    }
    addGroup('Recent aircraft', recentMatches);
    addGroup(recentMatches.length ? 'Other compatible aircraft' : 'Compatible aircraft', otherMatches);
    picker.value = shownSelection ? state.ac : '';
    const count = matches.length
      ? matches.length + ' aircraft available.'
      : words.length ? 'No compatible aircraft match this search.' : 'No compatible aircraft for this setup.';
    pickerStatus.textContent = [count, matches.length ? scope : ''].filter(Boolean).join(' ');
  }

  function renderAircraft() {
    const type = state.type || 'qf_bfm';
    const maps = mapOptions(type);
    const result = aircraftOptions(type, state.map ? [state.map] : maps);
    if (state.ac && !result.aircraft.some(aircraft => aircraft.key === state.ac)) {
      const fitsAnotherMap = state.map && !qfEra(type, state.map, state.ac) &&
        maps.some(map => qfEra(type, map, state.ac));
      if (!fitsAnotherMap) state.ac = null;
    }
    scope = result.scope;
    displayed = result.aircraft.map(aircraft => ({
      key: aircraft.key, id: aircraft.id, label: acDisplay(aircraft.key, aircraft.id),
    }));
    filterOptions();
  }

  function renderSummary(types, era) {
    const options = getOptions();
    const type = types.find(option => option.k === state.type);
    const aircraft = options.aircraft.find(aircraft => aircraft.key === state.ac);
    const map = options.maps[state.map];
    summary.textContent = [type?.t, aircraft && acDisplay(aircraft.key, aircraft.id), map?.label]
      .filter(Boolean).join(' · ') || 'Your sortie';
    if (!era || !aircraft || !map || !displayed.some(option => option.key === state.ac)) return;
    const {ac, bfm, spice, seed} = state;
    const moved = recent[0] !== ac;
    recent = [ac, ...recent.filter(key => key !== ac)].slice(0, historyLimit);
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        setup: {type: state.type, ac, map: state.map, bfm, spice, seed}, recent,
      }));
    } catch {
      // The picker remains usable with storage disabled.
    }
    if (moved) filterOptions();
  }

  search.addEventListener('input', filterOptions);
  picker.addEventListener('change', () => {
    if (picker.value) {
      pick('ac', picker.value);
    } else {
      state.ac = null;
      render();
    }
  });
  document.getElementById('qf_ownership').addEventListener('click', openOwn);
  document.addEventListener('sortie-ownership-change', () => {
    if (document.getElementById('quick').classList.contains('on') && getOptions()) render();
  });

  return {
    restore: recoverSetup,
    renderAircraft,
    renderSummary,
    canPickAircraft: key => displayed.some(aircraft => aircraft.key === key),
  };
}
