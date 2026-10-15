/** Personal mission browsing and explicit, revocable sharing. */
(()=>{
  'use strict';
  const $=id=>document.getElementById(id), dialog=$('shelf_dialog');
  const publicView=location.pathname.startsWith('/pilots/')||location.pathname.startsWith('/shared/');
  let account=null, data={items:[],page_path:null}, filter='all', busy=false;
  const categories={original:'Original files',setup:'Saved setup',library:'Library pick'};
  const aircraftNames={F_4E_45MC:'F-4E Phantom II',F_16C_50:'F-16C Viper',FA_18C_hornet:'F/A-18C Hornet',F_14B:'F-14B Tomcat',F_14A_135_GR:'F-14A Tomcat'};
  const maps={caucasus:'Caucasus',nevada:'Nevada',persiangulf:'Persian Gulf',syria:'Syria',germany:'Germany Cold War',sinai:'Sinai',iraq:'Iraq',afghanistan:'Afghanistan',marianas:'Marianas',normandy:'Normandy',thechannel:'The Channel',kola:'Kola',falklands:'South Atlantic'};
  function node(tag,text,className){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(className)e.className=className;return e;}
  function status(text){$('shelf_status').textContent=text;}
  function dstatus(text){$('dialog_status').textContent=text;}
  async function request(path,options={}){
    const response=await fetch(path,{...options,cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':account?.csrf||'',...options.headers}});
    if(!response.ok){let message='Could not load missions. Please try again.';try{const body=await response.json();if(typeof body.detail==='string')message=body.detail;}catch(e){}throw new Error(message);}
    return response.json();
  }
  function button(text,callback,primary=false){const b=node('button',text,primary?'primary':'');b.type='button';b.onclick=async()=>{if(busy)return;busy=true;b.disabled=true;try{await callback();}catch(e){(dialog.open?dstatus:status)(e.message);}finally{busy=false;b.disabled=false;}};return b;}
  function link(text,path,primary=false){const a=node('a',text,'button'+(primary?' primary':''));a.href=path;return a;}
  function absolute(path){return new URL(path,location.origin).href;}
  function modal(title){$('dialog_title').textContent=title;$('dialog_body').replaceChildren();dstatus('');if(!dialog.open)dialog.showModal();return $('dialog_body');}
  async function copy(path){try{await navigator.clipboard.writeText(absolute(path));dstatus('Link copied. You can paste it into Discord or a message.');}catch(e){dstatus('Copy the link from the field above; clipboard access is unavailable.');$('shared_url').focus();$('shared_url').select();}}
  function linkControls(body,path){
    const field=node('div',undefined,'share-link'),label=node('label','Share link');label.htmlFor='shared_url';
    const input=node('input');input.id='shared_url';input.type='text';input.readOnly=true;input.value=absolute(path);field.append(label,input);body.append(field);
    const actions=node('div',undefined,'actions');actions.append(button('Copy link',()=>copy(path),true));const preview=link('Preview shared page',path);preview.target='_blank';preview.rel='noreferrer';actions.append(preview);body.append(actions);
  }
  const facetKey=value=>String(value).split(/[—–]/)[0].replace(/[^a-z0-9]/gi,'').toLowerCase();
  function facetValues(item,type){
    const values=item.facets?.[type] || [item.details?.[type==='maps'?'map':'aircraft']].filter(Boolean);
    return values.length?values:['__unspecified'];
  }
  function facetLabel(value,type){
    if(value==='__unspecified')return 'Not specified';
    const labels=type==='maps'?maps:aircraftNames;
    return Object.entries(labels).find(([key])=>facetKey(key)===facetKey(value))?.[1] || value.replaceAll('_','-');
  }
  function updateFacets(){
    for(const [id,type,all] of [['mission_map','maps','All maps'],['mission_aircraft','aircraft','All aircraft']]){
      const select=$(id),previous=select.value,values=new Map();
      for(const item of data.items)for(const value of facetValues(item,type))values.set(facetKey(value),facetLabel(value,type));
      select.replaceChildren(new Option(all,''));
      for(const [key,label] of [...values].sort((a,b)=>a[1].localeCompare(b[1])))select.append(new Option(label,key));
      select.value=values.has(previous)?previous:'';
    }
  }
  async function reload(){data=await request('/api/account/library');updateFacets();$('share_page').textContent=data.page_path?'Manage page link':'Share my page';render();}
  function shareMission(item){
    const body=modal(item.share_path?'Share mission':'Share “'+item.title+'”');
    body.append(node('p','Anyone with this link can view your profile name and this mission’s settings or shared files. It will also appear on your shared page if you enable one. Your other missions stay private.'));
    body.append(node('p','Stopping sharing blocks future access. Files someone has already downloaded cannot be recalled.','mission-description'));
    if(item.share_path){linkControls(body,item.share_path);body.append(button('Stop sharing this mission',async()=>{await request('/api/account/shares/'+item.kind+'/'+item.id,{method:'DELETE'});dialog.close();await reload();status('Mission is private. Its old share link no longer works.');}));}
    else body.append(button('Create share link',async()=>{const result=await request('/api/account/shares',{method:'POST',body:JSON.stringify({kind:item.kind,id:item.id})});item.share_path=result.path;body.replaceChildren(node('p','This mission is now shared with anyone who has its link.'));linkControls(body,result.path);await reload();},true));
  }
  function sharePage(){
    const body=modal('Share my mission page');
    const shared=data.items.filter(i=>i.share_path).length;
    body.append(node('p','Your page shows your profile name and only missions you explicitly share. Anyone with the link can browse and download those shared missions. It is not listed in a public directory.'));
    body.append(node('p',shared+' shared '+(shared===1?'mission':'missions')+' · '+(data.items.length-shared)+' private. Use Share on a mission card to choose what appears.','mission-description'));
    if(data.page_path){linkControls(body,data.page_path);body.append(button('Stop all sharing',async()=>{if(!confirm('Stop your shared page and every individual mission link? Old links will stop working.'))return;await request('/api/account/shared-page',{method:'DELETE'});dialog.close();await reload();status('Your page and missions are private. All previous links have stopped working.');}));}
    else body.append(button('Enable shared page',async()=>{const result=await request('/api/account/shared-page',{method:'POST'});data.page_path=result.path;body.replaceChildren(node('p','Your page is available to anyone with this link. Only shared missions appear.'));if(!shared)body.append(node('p','Your shared page is empty. Close this dialog and choose Share on the missions you want to include.'));linkControls(body,result.path);await reload();},true));
  }
  function rename(item){const body=modal('Rename mission'),label=node('label','Mission name');label.htmlFor='rename_name';const input=node('input');input.id='rename_name';input.type='text';input.maxLength=80;input.value=item.title;body.append(label,input);body.append(button('Save name',async()=>{if(!input.value.trim()){dstatus('Enter a mission name.');input.focus();return;}await request('/api/account/'+(item.kind==='mission'?'missions':'selections')+'/'+item.id,{method:'PATCH',body:JSON.stringify({name:input.value.trim()})});dialog.close();await reload();status('Mission renamed.');},true));input.focus();input.select();}
  async function remove(item){if(!confirm('Remove “'+item.title+'” from your profile? Its shared link will also stop working.'+(item.category==='original'?' Download original files first.':'')))return;await request('/api/account/'+(item.kind==='mission'?'missions':'selections')+'/'+item.id,{method:'DELETE'});await reload();status('Mission removed. Any shared link has stopped working.');}
  function render(){
    const query=$('mission_search').value.trim().toLowerCase(),sort=$('mission_sort').value;
    const map=$('mission_map').value,aircraft=$('mission_aircraft').value;
    const items=data.items.filter(i=>(!map||facetValues(i,'maps').some(v=>facetKey(v)===map)) && (!aircraft||facetValues(i,'aircraft').some(v=>facetKey(v)===aircraft)) && (filter==='all'||(filter==='shared'?Boolean(i.share_path):i.category===filter)) && [i.title,i.details?.map,maps[i.details?.map],i.details?.aircraft,aircraftNames[i.details?.aircraft],i.details?.aircraft?.replaceAll('_','-'),i.details?.era,...facetValues(i,'maps').map(v=>facetLabel(v,'maps')),...facetValues(i,'aircraft').map(v=>facetLabel(v,'aircraft'))].join(' ').toLowerCase().includes(query));
    items.sort(sort==='title'?(a,b)=>a.title.localeCompare(b.title):sort==='oldest'?(a,b)=>a.created_at-b.created_at:(a,b)=>b.created_at-a.created_at);
    $('shelf_count').textContent=items.length+' '+(items.length===1?'mission':'missions')+(items.length!==data.items.length?' of '+data.items.length:'')+(publicView?' shared with you':' in your collection');
    const grid=$('mission_grid');grid.replaceChildren();
    if(!items.length){const empty=node('div',undefined,'empty-state');empty.append(node('h2',data.items.length?'No matching missions':publicView?'No missions shared yet':'Your next flight starts here'),node('p',data.items.length?'Try another search or show all mission types.':publicView?'The pilot has not shared any missions on this page yet.':'Save a mission from Library, Fly Now or Builder. It will be waiting here whenever you return.'));if(data.items.length)empty.append(button('Clear search and filters',()=>{$('mission_search').value='';$('mission_map').value='';$('mission_aircraft').value='';setFilter('all');}));else empty.append(link('Browse the Library','/?v=library',true));grid.append(empty);return;}
    for(const item of items){
      const card=node('article',undefined,'mission-card'),top=node('div',undefined,'card-top');
      top.append(node('span',item.category==='library'?(item.collection?'Library collection':'Published mission'):categories[item.category],'card-type'));
      if(!publicView)top.append(node('span',item.share_path?'Shared by link':'Private','visibility'+(item.share_path?' shared':'')));
      const title=node('h2',item.title);title.className='mission-title';card.append(top,title);
      const metadata=node('ul',undefined,'mission-meta');metadata.setAttribute('aria-label','Mission details');
      const d=item.details||{};for(const text of [maps[d.map]||d.map,aircraftNames[d.aircraft]||d.aircraft?.replaceAll('_','-'),d.era==='coldwar'?'Cold War':d.era==='modern'?'Modern':d.era==='ww2'?'WWII':d.era])if(text)metadata.append(node('li',text));
      if(d.slots)metadata.append(node('li',d.slots+' aircraft'+(d.veteran_wingmen?' · '+d.veteran_wingmen+' veteran AI':'')));
      card.append(metadata);
      const explanation=item.category==='original'?'Original .miz and matching Mission Kit, kept exactly as generated.':item.category==='setup'?'Saved settings and seed. Open in Builder to generate with the current release.':'A Library reference. Downloads use the currently published version.';
      card.append(node('p',explanation,'mission-description'));
      const actions=node('div',undefined,'actions');
      if(item.category==='original')actions.append(link('Download .miz',item.miz_path,true),link('Mission Kit',item.kit_path));
      else if(item.category==='setup')actions.append(link('Open in Builder',item.open_path,true));
      else actions.append(link(item.collection?'Download collection':'Download mission',item.download_path,true),link('View in Library',item.open_path));
      if(!publicView)actions.append(button(item.share_path?'Manage link':'Share',()=>shareMission(item)),button('Rename',()=>rename(item)));
      else if(item.share_path){const more=link('View mission',item.share_path);actions.append(more);}
      card.append(actions);
      if(publicView && item.category!=='original' && !item.pack_version){card.append(node('p','Saved '+new Date(item.created_at*1000).toLocaleDateString()+' · v'+item.version,'card-details'));grid.append(card);continue;}
      const details=node('details',undefined,'card-details'),summary=node('summary',(publicView?'Saved ':'Saved ')+new Date(item.created_at*1000).toLocaleDateString()+' · v'+item.version+(publicView?'':' · More actions'));details.append(summary);
      const extra=node('div',undefined,'actions');if(item.category==='original')extra.append(link('Open settings in Builder',item.open_path));
      if(item.pack_version)details.append(node('p','Selected Library version '+item.pack_version+'. Current publication may differ.'));
      if(!publicView)extra.append(button('Remove',()=>remove(item)));
      details.append(extra);card.append(details);grid.append(card);
    }
  }
  function setFilter(value){filter=value;document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===value)));render();}
  function settings(){
    const body=modal('Profile & saving settings'),profile=node('div',undefined,'settings-row');
    const label=node('label','Profile name');label.htmlFor='profile_name';const input=node('input');input.type='text';input.id='profile_name';input.maxLength=80;input.value=account.user.name;
    profile.append(label,input,node('small','This name appears beside missions and pages you choose to share.'),button('Save profile',async()=>{await request('/api/account',{method:'PATCH',body:JSON.stringify({name:input.value.trim()})});account=await request('/api/account');dstatus('Profile saved.');}));body.append(profile);
    const saves=node('div',undefined,'settings-row'),toggle=node('label',undefined,'toggle'),cb=node('input');cb.type='checkbox';cb.id='auto_save';cb.checked=true;try{cb.checked=localStorage.getItem('ss_save_missions')!=='off';}catch(e){}
    toggle.append(cb,node('span','Save newly generated missions on this browser'));saves.append(toggle,node('small','Keep up to 100 saved selections, plus 100 original missions or 100 MB. This browser preference does not change existing saves.'));
    cb.onchange=()=>{try{localStorage.setItem('ss_save_missions',cb.checked?'on':'off');dstatus('Saving preference updated for this browser.');}catch(e){cb.checked=!cb.checked;dstatus('Browser storage is unavailable. Sign out to generate as a guest without saving.');}};body.append(saves);
    const actions=node('div',undefined,'actions');actions.append(link('Export settings','/api/account/export'),button('Sign out',async()=>{await request('/api/account/logout',{method:'POST'});location.assign('/my-missions');}),button('Delete profile',async()=>{if(!confirm('Permanently delete this profile, all saved missions and every shared link? Download originals first.'))return;await request('/api/account',{method:'DELETE'});location.assign('/my-missions');}));body.append(actions);
  }
  function applyTheme(mode){document.body.dataset.mode=mode;$('shelf_theme').textContent=mode==='night'?'Light mode':'Dark mode';}
  let initial='paper';try{if(localStorage.getItem('fl_mode')==='night')initial='night';}catch(e){}applyTheme(initial);
  $('shelf_theme').onclick=()=>{const mode=document.body.dataset.mode==='night'?'paper':'night';applyTheme(mode);try{localStorage.setItem('fl_mode',mode);}catch(e){}};
  $('dialog_close').onclick=()=>dialog.close();$('mission_search').oninput=render;$('mission_sort').onchange=render;$('mission_map').onchange=render;$('mission_aircraft').onchange=render;
  document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>setFilter(b.dataset.filter));$('share_page').onclick=sharePage;$('settings_open').onclick=settings;
  async function init(){
    if(publicView){
      const parts=location.pathname.split('/'),type=parts[1]==='pilots'?'pilots':'shared';
      data=await request('/api/'+type+'/'+encodeURIComponent(parts[2]));
      $('shelf_title').textContent=type==='pilots'?data.name+'’s missions':data.items[0].title;
      $('shelf_eyebrow').textContent='SHARED BY '+data.name.toUpperCase();$('shelf_intro').textContent='Selected missions from '+data.name+'. Open a setup or download a shared mission to fly.';
      $('mission_search').previousElementSibling.textContent='Search shared missions';$('mission_search').placeholder='Search shared missions…';$('shared_filter').hidden=true;
      $('shelf_note').textContent='Shared with anyone who has this link. Library references use current published content; original files are retained downloads. No sign-in is needed to view.';
      $('shelf_controls').hidden=data.items.length<2;updateFacets();status('');render();return;
    }
    $('my_page_link').setAttribute('aria-current','page');
    const returnParams=new URLSearchParams(location.search),loginOutcome=returnParams.get('auth');
    if(loginOutcome){returnParams.delete('auth');history.replaceState(null,'',location.pathname+(returnParams.size?'?'+returnParams:''));}
    account=await request('/api/account');
    if(!account.enabled||!account.user){
      status(loginOutcome==='cancelled'?'Sign-in cancelled. You can try again or browse as a guest.':loginOutcome==='failed'?'Sign-in could not finish. Please try again.':'');const empty=node('div',undefined,'empty-state');empty.append(node('h2',account.enabled?'Your missions, ready when you are':'Profile saving is unavailable'),node('p',account.enabled?'Sign in with Discord to keep missions across devices and choose what to share. Your saves are private until you create a share link.':'Keep your downloaded missions and try again later. You can still use the Library and Builder.'));
      if(account.enabled)empty.append(link('Continue with Discord','/auth/discord?return_to=%2Fmy-missions',true));empty.append(link('Browse as a guest','/?v=library'));$('mission_grid').append(empty);return;
    }
    $('shelf_tools').hidden=false;$('shelf_controls').hidden=false;
    $('shelf_note').textContent='Private until you choose Share. Original files remain exact downloads; saved setups use the current generator; Library picks follow the current publication.';
    await reload();status('');
    if(loginOutcome==='signed_in')status('Signed in. Your missions are ready.');
  }
  init().catch(e=>{status(e.message);const actions=node('div',undefined,'actions');actions.append(button('Try again',()=>location.reload()),link('Browse the Library','/?v=library'));if(!publicView)actions.append(link('Sign in again','/auth/discord?return_to=%2Fmy-missions'));$('mission_grid').replaceChildren(actions);});
})();
