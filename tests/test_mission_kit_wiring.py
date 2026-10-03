"""Exercise asynchronous generation and document ownership with the real UI functions."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parent.parent
UI = (ROOT / 'frontend/index.html').read_text() + '\n' + (ROOT / 'frontend/assets/mission-results.js').read_text()


def function(name):
    match = re.search(rf'(?:async )?function {name}\s*\([^)]*\)\s*{{', UI)
    assert match, name
    start = match.end() - 1
    depth = 0
    for index in range(start, len(UI)):
        depth += (UI[index] == '{') - (UI[index] == '}')
        if not depth:
            return UI[match.start():index + 1]
    raise AssertionError(name)


def run_js(body, names):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js needed for frontend behavior tests')
    script = '\n'.join(function(name) for name in names) + '\n' + body
    result = subprocess.run([node, '-e', script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('source', ['builder', 'library', 'quick'])
def test_generation_waits_for_the_response_and_rejects_duplicate_requests(source):
    out = run_js("""
const statuses={textContent:''}, btn={innerHTML:'Generate'}, box={};
let GENERATING=false, LAST_GEN_RECIPE=null, MISSION_RESULTS={};
let requests=[], downloads=[], shown=[], finish;
const document={getElementById:()=>statuses};
let events=[];
const visitorId=()=> 'test', ga=(event,params)=>events.push({event,params}), syncGenerationButtons=()=>{};
const showKit=(result,target)=>shown.push({result,target});
const saveDownload=(blob,name)=>downloads.push(name);
const fetch=(url,opts)=>{requests.push(JSON.parse(opts.body));return new Promise(resolve=>finish=resolve);};
(async()=>{
 const rc={map:'caucasus',seed:1,corridors:['A']};
 const pending=generateMission(btn,{source:SOURCE,rc,box,status:statuses});
 rc.seed=2; rc.corridors.push('B');
 const duplicate=await generateMission(btn,{source:'quick',rc});
 const during={busy:GENERATING,status:statuses.textContent,downloads:downloads.length,duplicate};
 finish({ok:true,headers:{get:()=>null},blob:async()=> 'blob'});
 const result=await pending;
 console.log(JSON.stringify({during,requests,downloads,shown:shown.length,seed:result.rc.seed,
   corridors:result.rc.corridors,deepFrozen:Object.isFrozen(result.rc.corridors),
   last:LAST_GEN_RECIPE.seed,source:result.source,events,busy:GENERATING,label:btn.innerHTML,status:statuses.textContent}));
})();
""".replace("SOURCE",json.dumps(source)), ['freezeRecipe', 'generateMission'])
    assert out['during'] == {'busy': True, 'status': 'Generating…', 'downloads': 0, 'duplicate': None}
    assert len(out['requests']) == 1
    assert out['seed'] == out['last'] == 1
    assert out['corridors'] == ['A'] and out['deepFrozen']
    assert out['source'] == source and out['shown'] == 1
    assert out['events'] == [{'event': 'generate', 'params': {'source': source}}]
    assert out['downloads'] == ['starter.miz']
    assert not out['busy'] and out['label'] == 'Generate'
    assert out['status'].startswith('Download started')


@pytest.mark.parametrize('failure', ['api', 'proxy', 'network', 'blob'])
def test_failed_generation_never_replaces_the_successful_kit(failure):
    out = run_js("""
const statuses={textContent:''}, btn={innerHTML:'Generate'};
let GENERATING=false, LAST_GEN_RECIPE={seed:7}, MISSION_RESULTS={library:{rc:LAST_GEN_RECIPE}};
let drawn=0, downloaded=0;
const document={getElementById:()=>statuses};
const visitorId=()=> 'test', ga=()=>{}, syncGenerationButtons=()=>{};
const showKit=()=>drawn++, saveDownload=()=>downloaded++;
const failure=FAILURE;
const fetch=async()=>{
 if(failure==='network') throw new Error('Network unavailable');
 return {ok:failure==='blob',status:502,headers:{get:()=>null},
   json:async()=>{if(failure==='proxy') throw new Error('HTML');return {detail:'Invalid mission'};},
   blob:async()=>{throw new Error('Interrupted download');}};
};
(async()=>{const result=await generateMission(btn,{source:'library',rc:{seed:8},status:statuses});
 console.log(JSON.stringify({result,last:LAST_GEN_RECIPE.seed,kit:MISSION_RESULTS.library.rc.seed,
   drawn,downloaded,busy:GENERATING,status:statuses.textContent,label:btn.innerHTML}));})();
""".replace('FAILURE', json.dumps(failure)), ['freezeRecipe', 'responseError', 'generateMission'])
    assert out['result'] is None and out['last'] == out['kit'] == 7
    assert out['drawn'] == out['downloaded'] == 0 and not out['busy']
    assert out['label'] == 'Generate' and out['status'].startswith('Error:')
    assert 'Download started' not in out['status']


def test_each_kit_download_keeps_its_recipe_and_reports_status_in_its_own_view():
    out = run_js("""
let sent=[], saved=[];
const visitorId=()=> 'test',ga=()=>{};
const recipe=()=>({seed:999});
const saveDownload=(blob,name)=>saved.push(name);
const document={getElementById:()=>{throw new Error('global status used');}};
const fetch=async(url,opts)=>{sent.push({url,...JSON.parse(opts.body)});
 return {ok:true,headers:{get:()=>null},blob:async()=> 'zip'};};
function kit(seed,source){
 const status={textContent:''}; const brief={closest:()=>({querySelector:()=>status})},kb={...brief};
 const box={querySelector:q=>q==='.kit_brief'?brief:kb};
 const result={rc:{seed},source}; wireKitButtons(box,result);return {brief,kb,status};
}
(async()=>{const builder=kit(10,'builder'),quick=kit(20,'quick'),library=kit(30,'library');
 await builder.brief.onclick(); await quick.kb.onclick(); await library.brief.onclick();
 console.log(JSON.stringify({sent,statuses:[builder,quick,library].map(k=>k.status.textContent),saved}));})();
""", ['wireKitButtons', 'freezeRecipe', 'downloadDocument', 'downloadBrief', 'downloadKneeboard'])
    assert [(r['recipe']['seed'], r['source'], r['url']) for r in out['sent']] == [
        (10, 'builder', '/api/brief'), (20, 'quick', '/api/kneeboard'), (30, 'library', '/api/brief')]
    assert all('download started' in status for status in out['statuses'])


def test_no_timer_claims_library_generation_succeeded():
    assert 'setTimeout' not in function('generateFromLib')
    assert 'await generateMission' in function('generateFromLib')
    assert 'wireKitButtons(box, result)' in function('showKit')
    assert 'id="kit_brief"' not in UI and 'id="kit_kb"' not in UI
    assert 'KIT_TARGET' not in UI
