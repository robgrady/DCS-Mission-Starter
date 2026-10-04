/** The reference shelf has no recipe mutation or mission-generation actions. */
(() => {
  const get = id => document.getElementById(id);
  const cards = [...document.querySelectorAll('.reference-card')];
  function filter() {
    const map = get('history-map').value, period = get('history-period').value;
    const topic = get('history-topic').value, query = get('history-search').value.trim().toLocaleLowerCase();
    let visible = 0;
    for (const card of cards) {
      const maps = card.dataset.map.split(' ').filter(Boolean);
      card.hidden = !!((map && maps.length && !maps.includes(map)) ||
        (period && card.dataset.period !== period) || (topic && card.dataset.topic !== topic) ||
        (query && !card.textContent.toLocaleLowerCase().includes(query)));
      if (!card.hidden) visible++;
    }
    get('history-count').textContent = `${visible} reference reading${visible === 1 ? '' : 's'}`;
    get('history-empty').hidden = visible !== 0;
    for (const row of document.querySelectorAll('.unit-table tbody tr')) {
      row.hidden = !!(map && row.dataset.map !== map);
    }
    get('nevada-charts').hidden = !!(map && map !== 'nevada');
    if (period === 'nevada-1981' || period === 'nevada-2014') {
      get('history-profile').value = period;
      selectProfile();
    }
  }
  function selectProfile() {
    const id = get('history-profile').value;
    if (id !== 'nevada-1981') get('history-extent').value = 'overview';
    const view = get('history-extent').value;
    get('history-extent-label').hidden = id !== 'nevada-1981';
    for (const section of document.querySelectorAll('.reference-profile')) {
      section.hidden = section.dataset.profile !== id;
      for (const chart of section.querySelectorAll('.point-diagram')) chart.hidden = chart.dataset.view !== view;
    }
    for (const selected of document.querySelectorAll('.selected')) selected.classList.remove('selected');
    get('history-point-detail').textContent = 'Select a point for its coordinate row.';
    get('history-chart-download').href = `/api/historical-library/profiles/${id}/chart.svg?view=${view}`;
    get('history-profile-download').href = `/api/historical-library/profiles/${id}`;
  }
  function selectPoint(point) {
    for (const selected of document.querySelectorAll('.selected')) selected.classList.remove('selected');
    point.classList.add('selected');
    const section = point.closest('.reference-profile');
    const row = [...section.querySelectorAll('tr[data-point]')].find(r => r.dataset.point === point.dataset.point);
    if (row) {
      row.classList.add('selected');
      get('history-point-detail').textContent = row.textContent + ' · Source datum unverified.';
    }
  }
  for (const id of ['history-map','history-period','history-topic']) get(id).addEventListener('change', filter);
  get('history-search').addEventListener('input', filter);
  get('history-reset').addEventListener('click', () => {
    for (const id of ['history-map','history-period','history-topic','history-search']) get(id).value = '';
    filter();
  });
  for (const id of ['history-profile','history-extent']) get(id).addEventListener('change', selectProfile);
  for (const point of document.querySelectorAll('.reference-point')) {
    point.addEventListener('click', () => selectPoint(point));
    point.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); selectPoint(point);}
    });
  }
  get('history-on').addEventListener('input', () => {
    const day = get('history-on').value;
    for (const row of document.querySelectorAll('.unit-table tbody tr')) {
      const precision = row.dataset.precision, event = row.dataset.event;
      row.querySelector('.date-relation').textContent = !day ? 'Select a date to compare' :
        precision === 'circa' ? 'Approximate event; exact arrival unknown' :
        precision !== 'day' ? 'Month/year resolution; exact day unknown' :
        event === day ? 'Event on selected date' : event < day ? 'Earlier event; occupancy not certified' : 'Later event';
    }
  });
  // Direct reading links expose the cited article even after a filtered visit.
  const target = document.getElementById(location.hash.slice(1));
  if (target?.classList.contains('reference-card')) target.querySelector('details').open = true;
  selectProfile(); filter();
})();
