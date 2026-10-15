/** Optional private account UI. Native dialog owns focus, Escape and focus return. */
(() => {
  const dialog=document.getElementById('account_dialog');
  const button=document.getElementById('account_button');
  const content=document.getElementById('account_content');
  const status=document.getElementById('account_status');
  let state=null, opening=0, pending=null, saving=false;
  const pendingKey='ss_pending_selection';
  let savingPreference=true;
  try{savingPreference=localStorage.getItem('ss_save_missions')!=='off';}catch(e){}
  const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const message=value=>{status.textContent=value;};
  const saveEnabled=()=>savingPreference;

  async function request(path, options={}){
    const response=await fetch(path,{...options,cache:'no-store',headers:{
      'Content-Type':'application/json','X-CSRF-Token':state?.csrf||'',...options.headers}});
    if(!response.ok){
      let text='Request failed. Please try again.';
      try{const data=await response.json();if(typeof data.detail==='string')text=data.detail;}catch(e){}
      if(response.status===401){state={...state,user:null,csrf:null};button.textContent='Sign in';}
      throw new Error(text);
    }
    return response;
  }

  async function refresh(){
    state=await (await request('/api/account')).json();
    button.hidden=!state.enabled;
    button.textContent=state.user?'My missions':'Sign in';
  }

  function signIn(){
    // Builder already autosaves; take a final snapshot before leaving the page.
    try{if(typeof saveState==='function' && typeof OPT!=='undefined' && OPT)saveState();}catch(e){}
    if(pending){
      try{sessionStorage.setItem(pendingKey,JSON.stringify({selection:pending,expires:Date.now()+600000}));}
      catch(e){message('Browser storage is unavailable. After signing in, choose the mission again and click Save.');}
    }
    const params=new URLSearchParams(location.search);params.delete('auth');
    const returnTo='/'+(params.size?'?'+params.toString():'');
    location.assign('/auth/discord?'+new URLSearchParams({return_to:returnTo}));
  }

  function action(label, callback, primary=false){
    const b=document.createElement('button');b.type='button';b.textContent=label;
    if(primary)b.className='primary';
    b.onclick=async()=>{b.disabled=true;message('');try{await callback();}catch(e){message(e.message);}finally{b.disabled=false;}};
    return b;
  }

  function downloadLink(label, id, format){
    const a=document.createElement('a');a.textContent=label;
    a.href='/api/account/missions/'+encodeURIComponent(id)+'/download?format='+format;
    a.download=format==='miz'?'mission.miz':'mission_kit.zip';return a;
  }

  async function render(){
    const revision=++opening;
    content.replaceChildren();
    if(!state?.enabled){
      content.innerHTML='<p>Profile saving is unavailable on this server. Keep your downloaded missions or copy a share link from Builder. Guest generation remains available.</p>';return;
    }
    if(!state?.user){
      content.innerHTML='<p>Sign in with Discord to keep private missions across devices. Guest generation stays available.</p>'+
        '<p>We store your Discord ID, profile name, and missions you choose to save. We request no email or Discord server access. Signing in does not post to Discord.</p>'+
        (pending?'<p><b>Sign in to save this selection.</b> We will finish saving after you return from Discord if browser storage is available.</p>':'')+
        '<p>Use Save to My missions in Library or Builder to keep a selection before generating. After signing in, generated missions are saved by default. You can turn saving off here. Existing downloads and authored collection downloads are not imported.</p>';
      const actions=document.createElement('div');actions.className='account_actions';
      actions.append(action('Continue with Discord',signIn,true));content.append(actions);return;
    }
    content.innerHTML='<p>Your profile and missions are private. Signing in here currently applies to Sortie Starter.</p>'+
      '<details id="account_preferences" class="account_preferences"><summary>Profile &amp; saving settings</summary><label for="account_name">Profile name</label><input id="account_name" type="text" maxlength="80" value="'+esc(state.user.name)+'">'+
      '<div class="account_actions" id="profile_actions"></div>'+
      '<label class="account_toggle"><input id="account_save" type="checkbox" '+(saveEnabled()?'checked':'')+'> Save newly generated missions to my profile on this browser</label>'+
      '<p>Up to 100 missions or 100 MB per profile. Download original keeps the saved bytes; Edit in Builder generates a new mission with the current app. Download originals before deleting your profile.</p></details>'+
      '<h3>Saved selections</h3><p>Keep up to 100 mission setups or Library references. Settings generate with the current app; Library references open the current published content.</p>'+
      '<div id="account_selections">Loading saved selections…</div><h3>Generated missions</h3><div id="account_missions">Loading your missions…</div>';
    content.querySelector('#account_save').onchange=e=>{
      savingPreference=e.target.checked;
      try{localStorage.setItem('ss_save_missions',e.target.checked?'on':'off');}
      catch(err){message('Saving preference applies to this tab; browser storage is unavailable.');}
    };
    const actions=content.querySelector('#profile_actions');
    actions.append(action('Save profile',async()=>{
      const name=content.querySelector('#account_name').value.trim();
      await request('/api/account',{method:'PATCH',body:JSON.stringify({name})});
      await refresh();message('Profile saved.');
    }));
    const exportLink=document.createElement('a');exportLink.href='/api/account/export';
    exportLink.textContent='Export settings';exportLink.download='sortie-starter-profile.json';actions.append(exportLink);
    actions.append(action('Sign out',async()=>{await request('/api/account/logout',{method:'POST'});await refresh();await render();message('Signed out.');}));
    actions.append(action('Delete profile',async()=>{
      if(!confirm('Delete your Sortie Starter profile and all saved missions? Download your originals first. This cannot be undone.'))return;
      await request('/api/account',{method:'DELETE'});await refresh();await render();message('Profile and saved missions deleted.');
    }));
    const [data,selected]=await Promise.all([
      request('/api/account/missions').then(r=>r.json()), request('/api/account/selections').then(r=>r.json())]);
    if(revision!==opening || !state.user)return;
    const selections=content.querySelector('#account_selections');selections.replaceChildren();
    if(!selected.selections.length)selections.textContent='No saved selections yet. Choose a Library mission or collection, or review your Builder setup, then use Save to My missions.';
    for(const item of selected.selections){
      const payload=item.payload, card=document.createElement('article');card.className='account_mission';
      card.innerHTML='<h4>'+esc(item.title)+'</h4><small>'+esc(payload.kind==='recipe'?'Mission settings · saved with app v'+item.version:
        'Library reference · selected v'+(payload.pack_version||'unknown')+' · downloads use the current published version')+'</small>';
      const row=document.createElement('div');row.className='account_actions';
      if(payload.kind==='recipe')row.append(action('Open in Builder',()=>{
        if(typeof OPT==='undefined' || !OPT)throw new Error('Mission options are still loading. Please try again shortly.');
        applyRecipe(payload.recipe);saveState();dialog.close();closeDetail();showView('builder');showScreen('review');
      }));
      else {
        row.append(action('Open in Library',()=>{
          if(typeof OPT==='undefined' || !OPT)throw new Error('Library is still loading. Please try again shortly.');
          if(!libFind('pack_'+payload.pack_id))throw new Error('This collection is no longer published. You can remove this saved reference.');
          dialog.close();showView('library');openDetail('pack_'+payload.pack_id);
        }));
        const a=document.createElement('a');a.textContent=payload.path?'Download published mission':'Download published collection';
        a.href='/api/pack/'+encodeURIComponent(payload.pack_id)+'/'+(payload.path?payload.path.split('/').map(encodeURIComponent).join('/'):'all.zip');
        a.download='';row.append(a);
      }
      row.append(action('Rename',async()=>{
        const name=prompt('Selection name',item.title);if(name===null)return;
        await request('/api/account/selections/'+item.id,{method:'PATCH',body:JSON.stringify({name})});await render();message('Selection renamed.');
      }),action('Remove',async()=>{
        if(!confirm('Remove “'+item.title+'” from your saved selections?'))return;
        await request('/api/account/selections/'+item.id,{method:'DELETE'});await render();message('Selection removed.');
      }));
      card.append(row);selections.append(card);
    }
    const list=content.querySelector('#account_missions');list.replaceChildren();
    if(!data.missions.length){list.textContent='No saved missions yet. Generate from Fly now, Library or Builder with saving enabled.';return;}
    for(const item of data.missions){
      const card=document.createElement('article');card.className='account_mission';
      card.innerHTML='<h4>'+esc(item.title)+'</h4><small>'+esc(new Date(item.created_at*1000).toLocaleString())+
        ' · v'+esc(item.version)+' · '+esc(item.recipe.map)+' · '+esc(item.recipe.aircraft)+'</small>';
      const row=document.createElement('div');row.className='account_actions';
      row.append(downloadLink('Download original .miz',item.id,'miz'),downloadLink('Original Mission Kit',item.id,'kit'));
      row.append(action('Edit in Builder',()=>{
        if(typeof OPT==='undefined' || !OPT)throw new Error('Mission options are still loading. Please try again shortly.');
        applyRecipe(item.recipe);saveState();dialog.close();closeDetail();showView('builder');showScreen('review');
      }));
      row.append(action('Rename',async()=>{
        const name=prompt('Mission name',item.title);if(name===null)return;
        await request('/api/account/missions/'+item.id,{method:'PATCH',body:JSON.stringify({name})});await render();message('Mission renamed.');
      }));
      row.append(action('Delete',async()=>{
        if(!confirm('Delete “'+item.title+'” from your profile?'))return;
        await request('/api/account/missions/'+item.id,{method:'DELETE'});await render();message('Mission deleted.');
      }));
      card.append(row);list.append(card);
    }
  }

  async function open(){
    if(!dialog.open)dialog.showModal();message('Loading…');
    try{await refresh();message('');await render();}catch(e){message(e.message);}
  }
  async function saveSelection(selection){
    if(saving)return;
    saving=true;
    // Snapshot the actual click, not a URL or a later mutable Builder draft.
    pending=JSON.parse(JSON.stringify(selection));
    try{
      await refresh();
      if(!state.enabled)throw new Error('Sign-in is unavailable. Keep your download and try saving again later.');
      if(!state.user){await open();return;}
      if(!dialog.open)dialog.showModal();message('Saving selection…');
      await request('/api/account/selections',{method:'POST',body:JSON.stringify(pending)});
      pending=null;try{sessionStorage.removeItem(pendingKey);}catch(e){}
      await render();message('Saved to My missions. Find it under Saved selections.');
    }catch(e){if(!dialog.open)dialog.showModal();message(e.message);}
    finally{saving=false;}
  }
  button.onclick=open;
  document.getElementById('library_saved').onclick=open;
  document.getElementById('save_builder').onclick=()=>saveSelection({kind:'recipe',recipe:recipe()});
  document.getElementById('qf_save').onclick=()=>{
    const rc=qfRecipe();
    if(!rc.era){document.getElementById('qf_hint').textContent='Choose a mission, aircraft and map before saving.';return;}
    return saveSelection({kind:'recipe',recipe:rc});
  };
  document.getElementById('account_close').onclick=()=>dialog.close();
  window.SortieAccount={
    open, saveSelection,
    generationRequest(){return state?.user && saveEnabled()?{
      url:'/api/account/generate',headers:{'X-CSRF-Token':state.csrf,}}:{url:'/api/generate',headers:{}};},
    originalKit(id){return '/api/account/missions/'+encodeURIComponent(id)+'/download?format=kit';},
    get signedIn(){return Boolean(state?.user);}
  };
  const params=new URLSearchParams(location.search), outcome=params.get('auth');
  if(outcome){params.delete('auth');history.replaceState(history.state,'',location.pathname+(params.size?'?'+params:'')+location.hash);}
  refresh().then(async()=>{
    if(!outcome)return;
    try{
      const stored=JSON.parse(sessionStorage.getItem(pendingKey)||'null');sessionStorage.removeItem(pendingKey);
      if(stored?.expires>Date.now())pending=stored.selection;
    }catch(e){}
    if(outcome==='signed_in' && pending){await saveSelection(pending);return;}
    await open();message(outcome==='signed_in'?'Signed in. New generated missions will be saved unless you turn saving off.':
      outcome==='cancelled'?'Sign-in cancelled. You can continue generating as a guest.':'Sign-in could not finish. Please try again.');
  }).catch(()=>{button.hidden=false;button.textContent='Account unavailable';});
})();
