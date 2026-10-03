/** One catalog projection for cards, discovery, compatibility and configuration. */
function catalogToken(value){return String(value||'').split(' — ')[0].toLowerCase().replace(/hornet$/,'').replace(/[^a-z0-9]/g,'');}
function catalogAircraftKey(value, options){
 const token=catalogToken(value);
 return (options.aircraft||[]).find(a=>catalogToken(a.key)===token||catalogToken(a.id)===token)?.key||null;
}
function catalogMapKey(value, options){
 const token=catalogToken(value), aliases={nevada:['Nevada','Nevada (NTTR)'],normandy:['Normandy','Normandy 2'],falklands:['Falklands','South Atlantic'],germany:['Germany','Germany Cold War'],marianas:['MarianaIslands','Marianas']};
 return Object.keys(options.maps||{}).find(k=>[k,options.maps[k].label,...(aliases[k]||[])].some(s=>catalogToken(s)===token))||null;
}
function catalogOwnsAircraft(owned,key){
 if(!owned)return true;
 // These types ship in the same purchased module. Other variants remain distinct.
 const family=k=>/^F_14/.test(k)?'tomcat':/^Mirage_F1/.test(k)?'mirage-f1':/^P_47D/.test(k)?'p47':k;
 return [...owned].some(k=>family(k)===family(key));
}
function buildLibraryCatalog(t, options){
 const pack=t.pack, variants=[], aircraft=options.aircraft||[], maps=options.maps||{};
 const extras=[...new Set([...(typeof t.requires==='string'?[t.requires.replace(/^DCS:\s*/i,'')]:[]),...((t.needs_acls||t.recipe?.cq_ride)?['Supercarrier']:[])])];
 const requirements={maps:[],aircraft:[],extras,unknown:[]};
 if(pack){
  const req=pack.requires||{}, terrains=req.terrains?.length?req.terrains:(t.maps||[]);
  terrains.forEach((value,i)=>{const key=catalogMapKey(value,options);requirements.maps.push({key,label:req.terrain_names?.[i]||maps[key]?.label||value});if(!key)requirements.unknown.push(String(value));});
  (req.modules||[]).forEach(value=>{const key=catalogAircraftKey(value,options);if(key)requirements.aircraft.push(key);else if(/^(DCS:\s*)?Supercarrier$/i.test(value))requirements.extras.push('Supercarrier');else requirements.unknown.push(String(value));});
  if(!terrains.length||!(req.modules||[]).length)requirements.unknown.push('Incomplete collection requirements');
 }else{
  for(const era of t.eras||[]){
   const override=t.by_era?.[era]||{}, preferred=override.map||t.default_map||options.recipe_defaults?.map||'caucasus';
   const allowed=t.aircraft_locked?[preferred]:t.maps?.length?t.maps:Object.keys(maps);
   const candidates=[...new Set([preferred,...allowed])].filter(k=>allowed.includes(k)&&maps[k]?.presets?.[era]&&(!t.needs_carrier||maps[k].has_carrier));
   for(const map of candidates){
    const rc={...t.recipe,...override,...t.by_map?.[map]}, pin=rc.aircraft;
    const preset={...maps[map].presets[era],...(rc.lineup?maps[map].lineups?.[rc.lineup]:{})};
    if(rc.lineup&&!maps[map].lineups?.[rc.lineup])continue;
    if(rc.home_airbase&&rc.home_airbase!=='CARRIER'&&!(preset[(rc.coalition||'blue')+'_airbases']||[]).includes(rc.home_airbase))continue;
    if((rc.bb_carrier||rc.home_airbase==='CARRIER')&&!maps[map].has_carrier)continue;
    const choices=t.aircraft_choices?.[era]||[pin||options.recipe_defaults?.aircraft||'F_16C_50'];
    for(const key of choices){
     const a=aircraft.find(a=>a.key===key), w=options.eras?.[era]?.window, svc=a?.service;
     if(!a||a.upcoming)continue;
     if(!t.aircraft_locked&&w&&svc&&(svc[0]>w[1]||(svc[1]!==null&&svc[1]<w[0])))continue;
     variants.push({era,map,aircraft:key});
    }
   }
  }
 }
 const keys=pack?requirements.aircraft:[...new Set(variants.map(v=>v.aircraft))];
 const mapKeys=pack?requirements.maps.map(m=>m.key).filter(Boolean):[...new Set(variants.map(v=>v.map))];
 const activity=[...new Set([t.role,...(t.library?.activities||[]),...(t.needs_carrier?['carrier']:[]),...((t.recipe?.formation||t.recipe?.cq_ride||t.track)?['training']:[]),...(t.historical_context&&Object.values(t.historical_context).some(v=>Object.values(v).some(h=>h.classification&&h.classification!=='fictional_exercise'))?['historic']:[])])];
 return {structure:pack?'collection':'mission',subtype:pack?'Collection':t.kind==='full'?'Mission':'Open starter',count:pack?(pack.events||[]).length:1,title:t.title||t.label,aircraft:keys,maps:mapKeys,variants,requirements,activity};
}
function catalogCompatibility(catalog, ownedMaps, ownedAircraft, ownedModules, filters={}){
 const missingExtras=catalog.requirements.extras.filter(k=>ownedModules&&!ownedModules.has(k));
 if(catalog.structure==='collection'){
  const missing=[...catalog.requirements.maps.filter(m=>ownedMaps&&!ownedMaps.has(m.key)).map(m=>m.label),...catalog.aircraft.filter(k=>!catalogOwnsAircraft(ownedAircraft,k)),...missingExtras,...catalog.requirements.unknown];
  return {compatible:missing.length===0,missing,variant:null,unknown:catalog.requirements.unknown.length>0};
 }
 const matches=catalog.variants.filter(v=>(!filters.era||v.era===filters.era)&&(!filters.map||v.map===filters.map)&&(!filters.aircraft||v.aircraft===filters.aircraft));
 const variant=matches.find(v=>(!ownedMaps||ownedMaps.has(v.map))&&catalogOwnsAircraft(ownedAircraft,v.aircraft));
 return {compatible:!!variant&&!missingExtras.length,variant:variant||matches[0]||null,missing:[...(!variant?['No matching owned aircraft and terrain combination']:[]),...missingExtras],unknown:!catalog.variants.length};
}
