/** Authored route editor. No map/data request until the user opens it. */
function createRouteEditor({state:S, document, fetch, changed}) {
  const $ = id => document.getElementById(id);
  const clone = value => JSON.parse(JSON.stringify(value));
  let draft=[], selected=0, frame=null, signature='', generation=0, history=[], projection=null, fitted=false;
  const points=()=>S.engineSettings?.waypoints;
  const active=()=>Array.isArray(points());
  const status=text=>{$('route_status').textContent=text;};
  const snapshot=()=>({waypoints:clone(points()||[]),recovery:S.engineSettings?.route_recovery??null});
  function remember(){history.push(snapshot()); if(history.length>30)history.shift();}
  function commit(){draft=clone(points()||[]); signature=''; changed();}
  function restore(){signature='';history=[];draft=clone(points()||[]);selected=0;sync();}
  function sync(){
    $('route_mode').value=active()?'authored':'existing';
    $('route_custom').hidden=!active();
    const auto=$('bb_route'); if(auto)auto.disabled=active();
    if(!active())return;
    const next=JSON.stringify([S.map,points(),S.engineSettings?.route_recovery]);
    if(next===signature)return;
    signature=next; selected=Math.max(0,Math.min(selected,points().length-1));
    render(); load();
  }
  async function load(){
    const id=++generation, map=S.map;
    if(!map)return;
    status('Loading route schematic…');
    try{
      const response=await fetch('/api/route-preview',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({map,positions:points().map(p=>p.position)})});
      const data=await response.json();
      if(id!==generation||!active()||map!==S.map)return;
      if(!response.ok)throw Error(data.detail||'Unable to load route.');
      frame=data; recoveryChoices(); draw();
      status(points().length?`${points().length} waypoints · select a row or marker to edit. Click or drag to move the selected point.`:'Add your first waypoint. The aircraft start is configured separately.');
    }catch(error){if(id!==generation)return;frame=null;projection=null;$('route_map').replaceChildren();status('Route needs attention: '+error.message);}
  }
  function recoveryChoices(){
    const select=$('route_recovery'), value=S.engineSettings?.route_recovery??'';
    select.replaceChildren(new Option('End at last waypoint',''),new Option('Recover at home (airfield or carrier)','home'));
    for(const a of frame.airfields)select.add(new Option(a.name,a.name));
    if(value&&![...select.options].some(o=>o.value===value))select.add(new Option(value+' (check map)',value));
    select.value=value;
  }
  function render(){
    const list=$('route_list');list.replaceChildren();
    points().forEach((p,i)=>{
      const row=document.createElement('button');row.type='button';row.className='route-row'+(i===selected?' selected':'');
      row.textContent=String(i+1).padStart(2,'0')+'  '+p.name;
      row.setAttribute('aria-pressed',String(i===selected));row.onclick=()=>{selected=i;render();draw();$('wp_name').focus();};
      list.appendChild(row);
    });
    $('route_empty').hidden=points().length>0;$('route_fields').hidden=!points().length;
    $('route_add').disabled=points().length>=32;
    $('route_undo').disabled=!history.length;
    const p=points()[selected];if(!p)return;
    $('wp_name').value=p.name;$('wp_purpose').value=p.purpose||'transit';
    $('wp_system').value='lat'in p.position?'geo':'local';
    const geo=$('wp_system').value==='geo';
    $('wp_a_label').textContent=geo?'Latitude (decimal degrees)':'X north (metres)';
    $('wp_b_label').textContent=geo?'Longitude (decimal degrees)':'Y east (metres)';
    $('wp_a').value=geo?p.position.lat:p.position.x;$('wp_b').value=geo?p.position.lon:p.position.y;
    $('wp_alt').value=String(Math.round(p.altitude/0.3048*10)/10);
    $('wp_speed').value=String(Math.round(p.speed/0.5144444444444445*100)/100);
    $('route_up').disabled=selected===0;$('route_down').disabled=selected===points().length-1;
    $('route_point_label').textContent='Waypoint '+(selected+1)+' of '+points().length;
  }
  function svg(tag,attrs,text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v]of Object.entries(attrs))n.setAttribute(k,v);if(text!=null)n.textContent=text;return n;}
  function draw(){
    const map=$('route_map');map.replaceChildren(); if(!frame)return;
    let b=frame.bounds;
    if(fitted&&frame.points.length){
      const xs=frame.points.map(p=>p.x),ys=frame.points.map(p=>p.y),pad=10000;
      b={x_min:Math.min(...xs)-pad,x_max:Math.max(...xs)+pad,y_min:Math.min(...ys)-pad,y_max:Math.max(...ys)+pad};
    }
    const scale=Math.min(700/(b.y_max-b.y_min),370/(b.x_max-b.x_min));
    const left=400-(b.y_max-b.y_min)*scale/2,top=240-(b.x_max-b.x_min)*scale/2;
    const px=p=>[left+(p.y-b.y_min)*scale,top+(b.x_max-p.x)*scale];
    projection={scale,left,top,b};
    const bounds=frame.bounds, [edgeX,edgeY]=px({x:bounds.x_max,y:bounds.y_min});
    map.appendChild(svg('rect',{x:edgeX,y:edgeY,width:(bounds.y_max-bounds.y_min)*scale,height:(bounds.x_max-bounds.x_min)*scale,class:'route-envelope'}));
    map.appendChild(svg('text',{x:25,y:25,class:'route-map-label'},'N ↑  ·  DCS theatre schematic'));
    for(const a of frame.airfields){const [x,y]=px(a);const mark=svg('circle',{cx:x,cy:y,r:3,class:'route-airfield'});mark.appendChild(svg('title',{},a.name));map.appendChild(mark);}
    if(frame.points.length!==points().length)return;
    if(frame.points.length>1)map.appendChild(svg('polyline',{points:frame.points.map(p=>px(p).join(',')).join(' '),class:'route-line'}));
    frame.points.forEach((p,i)=>{
      const [x,y]=px(p),g=svg('g',{tabindex:0,role:'button','aria-label':'Select waypoint '+(i+1)+' '+points()[i].name,class:'route-marker'+(i===selected?' selected':'')});
      g.appendChild(svg('circle',{cx:x,cy:y,r:14}));g.appendChild(svg('text',{x,y:y+5,'text-anchor':'middle'},String(i+1)));
      g.appendChild(svg('title',{},points()[i].name));
      g.onclick=e=>{e.stopPropagation();selected=i;render();draw();};
      g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selected=i;render();draw();$('wp_name').focus();}};
      g.onpointerdown=e=>{e.stopPropagation();selected=i; map.setPointerCapture(e.pointerId);dragging=true;};
      map.appendChild(g);
    });
  }
  let dragging=false,dragMoved=false,suppressClick=false;
  function localAt(event){
    if(!projection)return null;
    const p=$('route_map').createSVGPoint();p.x=event.clientX;p.y=event.clientY;
    const q=p.matrixTransform($('route_map').getScreenCTM().inverse()),{scale,left,top,b}=projection;
    return {x:Math.round(b.x_max-(q.y-top)/scale),y:Math.round(b.y_min+(q.x-left)/scale)};
  }
  function move(event){
    if(!active()||!points().length)return;const pos=localAt(event);if(!pos)return;
    const b=frame.bounds;
    if(pos.x<b.x_min||pos.x>b.x_max||pos.y<b.y_min||pos.y>b.y_max){status('Choose a point inside the map authoring envelope.');return;}
    remember();points()[selected].position=pos;commit();
  }
  $('route_map').onpointermove=e=>{if(dragging)dragMoved=true;};
  $('route_map').onpointerup=e=>{if(dragging){dragging=false;if(dragMoved){dragMoved=false;suppressClick=true;move(e);}}};
  $('route_map').onpointercancel=()=>{dragging=false;dragMoved=false;};
  $('route_map').onclick=e=>{if(suppressClick){suppressClick=false;return;}if(e.target.closest('.route-marker'))return;move(e);};
  $('route_mode').onchange=()=>{
    S.engineSettings||={};
    if($('route_mode').value==='authored'){
      S.engineSettings.waypoints=clone(draft);S.engineSettings.route_recovery=null;
      $('bb_route').checked=false;
      $('timing_anchor').value='takeoff';$('timing_at').value='';$('timing_hold_min').value='0';
      $('timing_coach').checked=false;$('timing_package').checked=false;
    }else{draft=clone(points()||[]);delete S.engineSettings.waypoints;delete S.engineSettings.route_recovery;}
    signature='';changed();
  };
  $('route_add').onclick=()=>{
    if(!frame||points().length>=32){status('Wait for the schematic, or retry loading it.');return;}
    remember(); const b=frame.bounds,home=frame.airfields.find(a=>a.name===$('home').value);
    const last=frame.points.at(-1)||home||{x:(b.x_min+b.x_max)/2,y:(b.y_min+b.y_max)/2};
    let number=1;while(points().some(p=>p.id==='wp'+number||p.name==='WP'+number))number++;
    points().push({id:'wp'+number,name:'WP'+number,position:{x:last.x,y:Math.min(last.y+10000,b.y_max)},altitude:3048,speed:205.7777777777778,purpose:'transit'});
    selected=points().length-1;commit();
  };
  $('route_retry').onclick=load;
  $('route_fit').onclick=()=>{fitted=!fitted;$('route_fit').textContent=fitted?'Show theatre':'Fit route';draw();};
  $('route_recovery').onchange=()=>{remember();S.engineSettings.route_recovery=$('route_recovery').value||null;commit();};
  $('route_undo').onclick=()=>{const old=history.pop();if(!old)return;S.engineSettings.waypoints=old.waypoints;S.engineSettings.route_recovery=old.recovery;commit();};
  for(const [id,delta]of [['route_up',-1],['route_down',1]])$(id).onclick=()=>{remember();const j=selected+delta;[points()[selected],points()[j]]=[points()[j],points()[selected]];selected=j;commit();};
  $('route_delete').onclick=()=>{remember();points().splice(selected,1);commit();};
  function update(event){
    if(!event.target.reportValidity()){status('Invalid value was not applied.');render();return;}
    const name=$('wp_name').value.trim();
    if(!name||points().some((p,i)=>i!==selected&&p.name.toLowerCase()===name.toLowerCase())||name.toLowerCase()==='recovery'){status('Choose a unique waypoint name; RECOVERY is reserved.');render();return;}
    remember();const p=points()[selected];
    p.name=name;p.purpose=$('wp_purpose').value;
    if(event.target.id==='wp_alt')p.altitude=+$('wp_alt').value*0.3048;
    if(event.target.id==='wp_speed')p.speed=+$('wp_speed').value*0.5144444444444445;
    if(['wp_a','wp_b'].includes(event.target.id))p.position=$('wp_system').value==='geo'?{lat:+$('wp_a').value,lon:+$('wp_b').value}:{x:+$('wp_a').value,y:+$('wp_b').value};commit();
  }
  for(const id of ['wp_name','wp_alt','wp_speed','wp_a','wp_b','wp_purpose'])$(id).onchange=update;
  $('wp_system').onchange=()=>{
    const p=frame?.points[selected];if(!p){render();return;}
    remember();points()[selected].position=$('wp_system').value==='geo'?{lat:p.lat,lon:p.lon}:{x:p.x,y:p.y};commit();
  };
  return {sync,restore};
}
