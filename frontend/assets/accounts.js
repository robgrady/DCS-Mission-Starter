/** Optional private account UI. Native dialog owns focus, Escape and focus return. */
(() => {
  const dialog=document.getElementById('account_dialog');
  const button=document.getElementById('account_button');
  const content=document.getElementById('account_content');
  const status=document.getElementById('account_status');
  let state=null, pending=null, saving=false;
  const pendingKey='ss_pending_selection';
  let savingPreference=true;
  try{savingPreference=localStorage.getItem('ss_save_missions')!=='off';}catch(e){}

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

  async function render(){
    content.replaceChildren();
    if(!state?.enabled){
      content.innerHTML='<p>Profile saving is unavailable on this server. Keep your downloaded missions or copy a share link from Builder. Guest generation remains available.</p>';return;
    }
    if(!state?.user){
      content.innerHTML='<p>Keep your missions across devices and choose what to share. Your saves start private.</p>'+
        '<p>Discord provides your basic identity and profile name. We request no email or server access, and never post to Discord for you.</p>'+
        (pending?'<p><b>Sign in to save this selection.</b> We will finish saving after you return from Discord if browser storage is available.</p>':'')+
        '<p>Guest generation stays available. Existing downloads are not imported automatically.</p>';
      const actions=document.createElement('div');actions.className='account_actions';
      actions.append(action('Continue with Discord',signIn,true));content.append(actions);return;
    }
    content.innerHTML='<p>Your missions now have a full page with search, downloads and sharing controls.</p>';
    const shelf=document.createElement('a');shelf.href='/my-missions';shelf.textContent='View My missions';content.append(shelf);
  }

  async function openDialog(){
    if(!dialog.open)dialog.showModal();message('Loading…');
    try{await refresh();message('');await render();}catch(e){message(e.message);}
  }
  async function saveSelection(selection){
    if(saving)return;
    saving=true;
    // Snapshot the actual click, not a URL or a later mutable Builder draft.
    pending=JSON.parse(JSON.stringify(selection));
    try{
      if(state?.user)notice('Saving selection…');
      await refresh();
      if(!state.enabled)throw new Error('Sign-in is unavailable. Keep your download and try saving again later.');
      if(!state.user){await openDialog();return;}
      notice('Saving selection…');
      await request('/api/account/selections',{method:'POST',body:JSON.stringify(pending)});
      pending=null;try{sessionStorage.removeItem(pendingKey);}catch(e){}
      if(dialog.open)dialog.close();notice('Saved to My missions.');
    }catch(e){if(dialog.open)message(e.message);else notice(e.message,true);}
    finally{saving=false;}
  }
  function notice(text,retry=false){
    let box=document.getElementById('save_notice');
    if(!box){box=document.createElement('div');box.id='save_notice';box.setAttribute('role','status');box.setAttribute('aria-live','polite');document.body.append(box);}
    box.replaceChildren();const label=document.createElement('span');label.textContent=text;box.append(label);
    if(retry && pending){const again=document.createElement('button');again.type='button';again.textContent='Try saving again';again.onclick=()=>saveSelection(pending);box.append(again);}
    const view=document.createElement('a');view.href='/my-missions';view.textContent='View My missions';box.append(view);
    const close=document.createElement('button');close.type='button';close.textContent='Dismiss';close.onclick=()=>box.remove();box.append(close);
  }
  function open(){if(state?.user)location.assign('/my-missions');else return openDialog();}
  button.onclick=open;
  document.getElementById('library_saved').onclick=()=>location.assign('/my-missions');
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
  window.addEventListener('storage',event=>{if(event.key==='ss_save_missions')savingPreference=event.newValue!=='off';});
  refresh().then(async()=>{
    if(!outcome)return;
    try{
      const stored=JSON.parse(sessionStorage.getItem(pendingKey)||'null');sessionStorage.removeItem(pendingKey);
      if(stored?.expires>Date.now())pending=stored.selection;
    }catch(e){}
    if(outcome==='signed_in' && pending){await saveSelection(pending);return;}
    if(outcome==='signed_in'){location.assign('/my-missions');return;}
    await openDialog();message(outcome==='signed_in'?'Signed in. New generated missions will be saved unless you turn saving off.':
      outcome==='cancelled'?'Sign-in cancelled. You can continue generating as a guest.':'Sign-in could not finish. Please try again.');
  }).catch(()=>{button.hidden=false;button.textContent='Account unavailable';});
})();
