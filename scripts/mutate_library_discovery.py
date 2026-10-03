"""Prove Library compatibility, selection and layout promises in a real browser."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
CASES=[
 ('frontend/assets/library-controller.js', "mods.map(esc).join('</b>, <b>')", "mods.join('</b>, <b>')",'authored_requirements','authored requirement text becomes HTML'),
 ('frontend/assets/library-controller.js', "String(name).split('/').map(encodeURIComponent).join('/')", "String(name)",'authored_requirements','authored filename escapes its link attribute'),
 ('frontend/assets/library-controller.js', '||(pref?libCompatibility(t,pref).variant:null)', '','preferred_training','training preference lost behind an unrelated filter'),
 ('frontend/assets/library-controller.js', "if(filters.aircraft&&!c.aircraft.includes(filters.aircraft))return false;", "if(filters.aircraft&&t.aircraft!==filters.aircraft)return false;",'aircraft_and_map','aircraft filter loses collections and alternatives'),
 ('frontend/assets/library-catalog.js', 'catalog.requirements.maps.filter(m=>ownedMaps&&!ownedMaps.has(m.key))', 'catalog.requirements.maps.slice(0,1).filter(m=>ownedMaps&&!ownedMaps.has(m.key))','fixed_collections','additional terrain ignored'),
 ('frontend/assets/library-catalog.js', 'catalog.aircraft.filter(k=>!catalogOwnsAircraft(ownedAircraft,k))', '[]','fixed_collections','fixed aircraft ignored'),
 ('frontend/assets/library-catalog.js', 'catalog.requirements.extras.filter(k=>ownedModules&&!ownedModules.has(k))', '[]','fixed_collections','Supercarrier ignored'),
 ('frontend/assets/library-catalog.js', '...missingExtras,...catalog.requirements.unknown', '...missingExtras','unknown_collection','unknown requirement advertised as owned'),
 ('frontend/assets/library-controller.js', 'const filters={...libFilters(),...pref};', 'const filters=pref||{};','matching_owned_variant','filtered combination lost on opening detail'),
 ('frontend/assets/library-controller.js', 'const mc=document.querySelector(\'#maps .card[data-k="\'+map+\'"]\');', 'const mc=document.querySelector(\'#maps .card[data-k="caucasus"]\');','matching_owned_variant','chosen map lost when configuring Builder'),
 ('frontend/assets/library-controller.js', "document.getElementById('dMaps').innerHTML=detailMapRow(t);refreshDetailSummary(t);", "document.getElementById('dMaps').innerHTML=detailMapRow(t);",'detail_summary','summary stays in old era'),
 ('frontend/assets/library-controller.js', 'list.filter(t=>t.featured).slice(0,3)', 'list.filter(t=>t.featured).slice(0,21)','catalog_layout','recommendations overrun catalog'),
 ('frontend/assets/library-controller.js', 'list.filter(t=>!keys.has(t.k)).map(libCard)', 'list.map(libCard)','catalog_layout','featured items duplicated'),
 ('frontend/assets/library-catalog.js', 'title:t.title||t.label,', "title:(t.title||t.label).split(' — ')[0],",'catalog_layout','collection subtitles lost'),
 ('frontend/assets/library-controller.js', "return '<span>Threat: '+(names[n]||n)+' '+s+'</span>';", 'return s;','catalog_layout','threat loses text equivalent'),
 ('frontend/assets/library-controller.js', "modules:[...ownEdit.modules]", 'modules:[]','declared_supercarrier','additional module ownership is discarded'),
 ('frontend/index.html', '.dcta button,.dcta a.prime{border:none;', '.dcta button{border:none;','catalog_layout','collection download loses button sizing'),
]


def run(selector):
 return subprocess.run([sys.executable,'-m','pytest','tests/test_library_discovery.py','-q','-x','-k',selector],cwd=ROOT,capture_output=True,text=True)


def main():
 selected=[c for c in CASES if not sys.argv[1:] or any(fragment in c[-1] for fragment in sys.argv[1:])]
 assert selected,'No selected mutation'
 selector=' or '.join(sorted({c[3] for c in selected})) if sys.argv[1:] else ''
 baseline=run(selector);assert baseline.returncode==0,baseline.stdout+baseline.stderr
 originals={name:(ROOT/name).read_text() for name,*_ in selected}
 try:
  for name,anchor,replacement,case_selector,label in selected:
   original=originals[name];assert original.count(anchor)==1,(name,anchor,original.count(anchor))
   (ROOT/name).write_text(original.replace(anchor,replacement))
   try:
    result=run(case_selector)
    if result.returncode!=1:raise SystemExit(f'WEAK or invalid: {label}\n{result.stdout}\n{result.stderr}')
    print('caught:',label,flush=True)
   finally:(ROOT/name).write_text(original)
 finally:
  for name,original in originals.items():(ROOT/name).write_text(original)
 restored=run(selector);assert restored.returncode==0,restored.stdout+restored.stderr
 print(f'{len(selected)} caught; 0 weak; baseline restored and rechecked.')


if __name__=='__main__':main()
