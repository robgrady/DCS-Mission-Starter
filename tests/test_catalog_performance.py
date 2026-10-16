"""Guard repeated startup work without machine-dependent timing thresholds."""
from collections import Counter
import builtins
from pathlib import Path

from server.catalog_routes import options
from missiongen.historical_world import preview, template_previews


def test_options_bounds_historical_input_reads_instead_of_thousands(monkeypatch):
    counts=Counter(); original=builtins.open
    def tracked(path,*args,**kwargs):
        counts[Path(path).name] += 1
        return original(path,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(builtins,'open',tracked)
        data=options()
    # Cold map projections and supporting catalogs may read their own inputs.
    # The historical preview loop previously read these files ~5,000 times.
    assert sum(counts[name] for name in ('maps.json','eras.json','mission_templates.json')) <= 250, counts
    assert data['maps']['syria']['presets']['coldwar']['historical_context'] == preview('syria','coldwar')
    assert data['templates']['form_close']['historical_context'] == template_previews('form_close')


def test_library_catalog_reuses_projection_and_invalidates_nested_edits():
    import json, shutil, subprocess
    from ui_source import ROOT
    source=(ROOT/'frontend/assets/library-controller.js').read_text()
    # Exercise the actual controller: no DOM rendering needed to project items.
    script=source+'''
let builds=0;
function buildLibraryCatalog(t,opt){builds++;return {title:t.label,requirements:t.pack.requires};}
let options={templates:{pack_demo:{label:'Demo',pack:{requires:{modules:['Known']}}}},maps:{},eras:{},aircraft:[]};
const lib=createLibraryController({state:{},getOptions:()=>options,callbacks:{},environment:{}});
const first=lib.libItems();lib.libItems();lib.libItems();
if(builds!==1)throw new Error('catalog recomputed without an input change');
options.templates.pack_demo.pack.requires.modules.push('Unknown');
const second=lib.libItems();
if(builds!==2||first===second)throw new Error('nested edit was not invalidated');
console.log(JSON.stringify({builds}));
'''
    result=subprocess.run([shutil.which('node'),'-e',script],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['builds']==2
