/* Pure preset calculations. Callers supply catalog/state; no DOM or globals. */
function effectiveScenarioPreset(options, key, era, map){
  const template = options.templates[key] || {};
  const recipe = Object.assign({}, template.recipe || {}, (template.by_era || {})[era] || {});
  recipe.era = era;
  recipe.map = map || recipe.map || template.default_map || 'caucasus';
  Object.assign(recipe, (template.by_map || {})[recipe.map] || {});
  recipe.map = map || recipe.map || template.default_map || 'caucasus';
  if (recipe.bb_carrier && !recipe.home_airbase) recipe.home_airbase = 'CARRIER';
  return recipe;
}
function effectiveMapPreset(options, mapKey, era, lineup){
  const map = options.maps[mapKey];
  return {...map.presets[era], ...(map.lineups || {})[lineup]};
}
