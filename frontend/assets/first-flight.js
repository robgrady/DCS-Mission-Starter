function nonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function safeLink(value, sameOrigin = false) {
  if (!nonEmptyString(value)) return null;
  try {
    const url = new URL(value, location.origin);
    const web = url.protocol === 'https:' || url.protocol === 'http:';
    return web && (!sameOrigin || url.origin === location.origin) ? url : null;
  } catch {
    return null;
  }
}

function isOption(value) {
  return nonEmptyString(value?.id) && nonEmptyString(value.label);
}

function isProfile(profile) {
  return profile && isOption(profile.map) && isOption(profile.aircraft) &&
    nonEmptyString(profile.airfield) && safeLink(profile.download_url, true) &&
    Array.isArray(profile.lessons) && profile.lessons.length > 0 &&
    profile.lessons.every(lesson => nonEmptyString(lesson?.title) && nonEmptyString(lesson.start) &&
      nonEmptyString(lesson.objective) && safeLink(lesson.brief_url, true) &&
      safeLink(lesson.mission_url, true));
}

function fillOptions(select, options, preferred) {
  const choices = new Map(options.map(option => [option.id, option.label]));
  select.replaceChildren(...Array.from(choices, ([id, label]) => new Option(label, id)));
  if (choices.has(preferred)) select.value = preferred;
}

function lessonEntry(lesson) {
  const item = document.createElement('li');
  const title = document.createElement('h4');
  const objective = document.createElement('p');
  const details = document.createElement('p');
  const actions = document.createElement('div');
  const preview = document.createElement('a');
  const mission = document.createElement('a');
  title.textContent = lesson.title;
  objective.textContent = lesson.objective;
  details.textContent = Number.isFinite(lesson.minutes) && lesson.minutes > 0 ?
    `${lesson.start} · About ${lesson.minutes} min` : lesson.start;
  actions.className = 'first-flight-actions';
  preview.className = 'navbtn ghost';
  preview.href = safeLink(lesson.brief_url, true).href;
  preview.target = '_blank';
  preview.rel = 'noopener';
  preview.textContent = 'Preview brief';
  preview.setAttribute('aria-label', `Preview brief for ${lesson.title} (PDF, opens in a new tab)`);
  mission.className = 'navbtn ghost';
  mission.href = safeLink(lesson.mission_url, true).href;
  mission.download = '';
  mission.textContent = 'Download mission';
  mission.setAttribute('aria-label', `Download mission for ${lesson.title} (.miz)`);
  actions.append(preview, mission);
  item.append(title, objective, details, actions);
  return item;
}

function requirementsList(list) {
  return list.filter(item => nonEmptyString(item?.label)).map(item => {
    const entry = document.createElement('li');
    const url = safeLink(item.url);
    if (url) {
      const link = document.createElement('a');
      link.href = url.href;
      link.textContent = item.label;
      entry.append(link);
    } else {
      entry.textContent = item.label;
    }
    return entry;
  });
}

export async function loadFirstFlight(root) {
  const get = name => root.querySelector(`#first_flight_${name}`);
  const status = get('status');
  const retry = get('retry');
  const setup = get('setup');
  const review = get('review');
  const showUnavailable = message => {
    setup.hidden = true;
    review.hidden = true;
    status.textContent = message;
    status.hidden = false;
    retry.hidden = false;
    return false;
  };
  let available;
  try {
    const response = await fetch('/api/first-flight');
    if (!response.ok) throw new Error('First Flight catalog unavailable');
    const {profiles} = await response.json();
    if (!Array.isArray(profiles)) throw new Error('Invalid First Flight catalog');
    if (!profiles.length) return showUnavailable('No First Flight campaign is available right now.');
    available = profiles.filter(isProfile);
    if (!available.length) throw new Error('No valid First Flight options');
  } catch {
    return showUnavailable('Could not load First Flight. Try again.');
  }

  const map = get('map');
  const aircraft = get('aircraft');
  const download = get('download');
  const requirementsSection = get('requirements_section');
  download.parentElement.before(requirementsSection);
  const currentProfile = () => available.find(profile =>
    profile.map.id === map.value && profile.aircraft.id === aircraft.value);
  const updateAirfield = () => {
    get('airfield').textContent = `Training airfield · ${currentProfile().airfield}`;
  };
  const updateAircraft = () => {
    const aircraftOptions = available.filter(profile => profile.map.id === map.value).map(profile => profile.aircraft);
    fillOptions(aircraft, aircraftOptions, aircraft.value);
    updateAirfield();
  };
  fillOptions(map, available.map(profile => profile.map));
  updateAircraft();
  map.addEventListener('change', updateAircraft);
  aircraft.addEventListener('change', updateAirfield);

  setup.addEventListener('submit', event => {
    event.preventDefault();
    const profile = currentProfile();
    if (!profile) return;
    get('profile').textContent = `${profile.aircraft.label} · ${profile.map.label} · ${profile.airfield}`;
    get('lessons').replaceChildren(...profile.lessons.map(lessonEntry));
    const requirements = requirementsList(Array.isArray(profile.requirements) ? profile.requirements : []);
    get('requirements').replaceChildren(...requirements);
    requirementsSection.hidden = requirements.length === 0;
    const evidence = profile.status === 'flight_tested' ? 'Flight tested in DCS' : 'Flight testing pending';
    get('evidence').textContent = nonEmptyString(profile.version) ? `${evidence} · Pack v${profile.version}` : evidence;
    download.href = safeLink(profile.download_url, true).href;
    setup.hidden = true;
    review.hidden = false;
    get('review_title').focus();
  });
  get('back').addEventListener('click', () => {
    review.hidden = true;
    setup.hidden = false;
    map.focus();
  });
  status.hidden = true;
  retry.hidden = true;
  setup.hidden = false;
  return true;
}
