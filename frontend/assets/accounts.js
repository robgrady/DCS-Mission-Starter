/** Optional private account UI. Native dialog owns focus, Escape and focus return. */
(() => {
  const dialog=document.getElementById('account_dialog');
  const button=document.getElementById('account_button');
  const content=document.getElementById('account_content');
  const status=document.getElementById('account_status');
  let state=null, opening=0;
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
    if(!state?.user){
      content.innerHTML='<p>Sign in with Discord to keep private missions across devices. Guest generation stays available.</p>'+
        '<p>We store your Discord ID, profile name, and missions you choose to save. We request no email or Discord server access. Signing in does not post to Discord.</p>'+
        '<p>After signing in, generated missions are saved by default. You can turn saving off here. Existing downloads and authored collection downloads are not imported.</p>';
      const actions=document.createElement('div');actions.className='account_actions';
      actions.append(action('Continue with Discord',signIn,true));content.append(actions);return;
    }
    content.innerHTML='<p>Your profile and missions are private. Signing in here currently applies to Sortie Starter.</p>'+
      '<label for="account_name">Profile name</label><input id="account_name" type="text" maxlength="80" value="'+esc(state.user.name)+'">'+
      '<div class="account_actions" id="profile_actions"></div>'+
      '<label class="account_toggle"><input id="account_save" type="checkbox" '+(saveEnabled()?'checked':'')+'> Save newly generated missions to my profile on this browser</label>'+
      '<p>Up to 100 missions or 100 MB per profile. Download original keeps the saved bytes; Edit in Builder generates a new mission with the current app. Download originals before deleting your profile.</p>'+
      '<h3>My missions</h3><div id="account_missions">Loading your missions…</div>';
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
    const data=await (await request('/api/account/missions')).json();
    if(revision!==opening || !state.user)return;
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
        applyRecipe(item.recipe);saveState();dialog.close();showView('builder');showScreen('review');
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
  button.onclick=open;
  document.getElementById('account_close').onclick=()=>dialog.close();
  window.SortieAccount={
    open,
    generationRequest(){return state?.user && saveEnabled()?{
      url:'/api/account/generate',headers:{'X-CSRF-Token':state.csrf,}}:{url:'/api/generate',headers:{}};},
    originalKit(id){return '/api/account/missions/'+encodeURIComponent(id)+'/download?format=kit';},
    get signedIn(){return Boolean(state?.user);}
  };
  const params=new URLSearchParams(location.search), outcome=params.get('auth');
  if(outcome){params.delete('auth');history.replaceState(history.state,'',location.pathname+(params.size?'?'+params:'')+location.hash);}
  refresh().then(async()=>{
    if(!outcome)return;
    await open();message(outcome==='signed_in'?'Signed in. New generated missions will be saved unless you turn saving off.':
      outcome==='cancelled'?'Sign-in cancelled. You can continue generating as a guest.':'Sign-in could not finish. Please try again.');
  }).catch(()=>{button.hidden=false;button.textContent='Account unavailable';});
})();
