/** One selection card for every generation door; stale responses cannot replace newer picks. */
function createReadinessController({document, fetch, ownedMaps, ownedAc, ownedModules, esc}) {
 const pending = new WeakMap();
 function render(box, report) {
  const maps=ownedMaps(), aircraft=ownedAc(), modules=ownedModules();
  function hasRequirement(r) {
   if(r.free)return true;
   if(r.ownership?.aircraft)return !aircraft || catalogOwnsAircraft(aircraft,r.ownership.aircraft);
   if(r.ownership?.map)return !maps || maps.has(r.ownership.map);
   return r.kind==='map'?!maps||maps.has(r.key):r.kind==='aircraft'?!aircraft||catalogOwnsAircraft(aircraft,r.key):!modules||modules.has(r.key);
  }
  const missing=(report.requirements||[]).filter(r=>!hasRequirement(r));
  const owned=maps!==null;
  const lines=[['Requires',(report.requirements||[]).map(r=>r.label+(r.free?' (included)':'')).join(' · ')],
   ['Your content',missing.length?'Ownership not confirmed: '+missing.map(r=>r.label).join(', ')+'. Check your installed content and the listed dependencies.':owned?'Matches your declared content; installation has not been inspected.':'Ownership not set. Declare your modules in Library → My DCS content.'],
   ['Flight',report.flight.text], ['Departure',report.parking.home+' — '+report.parking.text],
   ['Equipment',report.equipment],['Dependencies',report.dependencies+' '+report.crew],['Validation','Selection checked · file not built yet · DCS flight unverified. App v'+report.app_version+'.']];
  box.innerHTML='<h4>Mission readiness</h4><dl>'+lines.map(([key,value])=>'<div><dt>'+esc(key)+'</dt><dd>'+esc(value)+'</dd></div>').join('')+'</dl>'+
   (report.warnings.length?'<div class="readiness-notes"><h5>Preparation notes ('+report.warnings.length+')</h5><ul>'+report.warnings.map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul></div>':'');
 }
 async function refresh(id, value) {
  const box=document.getElementById(id); if(!box)return;
  const token={}; pending.set(box,token);
  box.innerHTML='<h4>Mission readiness</h4><p role="status">Checking selections…</p>';
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),10000);
  try {
   const response=await fetch('/api/readiness',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({recipe:value}),signal:controller.signal});
   const data=await response.json();
   if(pending.get(box)!==token || !box.isConnected)return;
   if(!response.ok){box.innerHTML='<h4>Check this setup</h4><p>'+esc(typeof data.detail==='string'?data.detail:'Readiness check unavailable. Generation will validate your selections.')+'</p>';return;}
   render(box,data);
  } catch(e) {
   if(pending.get(box)===token && box.isConnected)box.innerHTML='<h4>Mission readiness</h4><p>Check unavailable. Generate will still validate your selections.</p>';
  } finally { clearTimeout(timer); }
 }
 function clear(id) {
  const box=document.getElementById(id); if(!box)return;
  pending.delete(box); box.textContent='';
 }
 return {refresh,clear};
}
