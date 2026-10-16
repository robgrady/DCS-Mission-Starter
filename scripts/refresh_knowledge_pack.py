"""Copy-first refresh of an existing private agent knowledge handoff.

Run after committing a release. Preserves the previous pack and its historical
narrative; refreshes copied project sources, terrain inventory and MCP contract.
Never uploads the private pack. The previous pack's allowlisted manifest owns
which private research notes are carried forward; original PDFs are not scanned.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'vendor')]


def details(path):
    return {'bytes':path.stat().st_size, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def member(root, name):
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('manifest paths must be relative and contained')
    path = (root/relative).resolve()
    if root not in path.parents:
        raise ValueError('manifest path escapes its root')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pack-version', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+', args.pack_version):
        parser.error('pack-version must be X.Y.Z')
    previous, out = args.previous.resolve(), args.output.resolve()
    if out == previous or previous in out.parents or out.exists():
        parser.error('output must be a new directory outside the previous pack')
    archive = out.parent/('Sortie-Starter-Mission-Making-Knowledge-'+args.pack_version+'.zip')
    if archive.exists():
        parser.error('archive already exists; use a new pack version')
    commit = subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'], text=True).strip()
    if subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True).strip():
        parser.error('commit the validated release before capturing its knowledge snapshot')
    old = json.loads((previous/'BUNDLE_MANIFEST.json').read_text())
    # Copy only verified payloads, not arbitrary private files beside the pack.
    for row in old['files']:
        src = member(previous, row['path'])
        if details(src) != {k:row[k] for k in ('bytes','sha256')}:
            parser.error('previous payload is outside the pack or differs from its manifest: '+row['path'])
    out.mkdir(parents=True)
    for row in old['files']:
        target = member(out, row['path'])
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(previous/row['path'], target)
    sources = json.loads((out/'SOURCE_MANIFEST.json').read_text())
    for row in sources['sources']:
        if row['origin'] == 'project':
            source = member(ROOT, row['source'])
            shutil.copyfile(source, member(out, row['bundle']))
        row.update(details(member(out, row['bundle'])))
    (out/'SOURCE_MANIFEST.json').write_text(json.dumps(sources,indent=2)+'\n')
    from missiongen import __version__
    from missiongen.map_bounds import catalog_bounds
    from missiongen.resolver import load_json
    from server.recipe_contract import recipe_json_schema
    (out/'data/recipe-schema.json').write_text(json.dumps(recipe_json_schema(),indent=2)+'\n')
    (out/'data/map-authoring-bounds.json').write_text(json.dumps({
        'app_version':__version__, 'source_commit':commit,
        'maps':{key:catalog_bounds(key) for key in load_json('maps')}},indent=2)+'\n')
    subprocess.run([sys.executable,str(out/'tools/capture_snapshot.py'),
                    '--repo',str(ROOT),'--output',str(out/'data')],check=True)
    now = datetime.now(timezone.utc).isoformat()
    current = (f'Knowledge pack {args.pack_version}; refreshed {now}. Project/MCP snapshot: '
               f'Sortie Starter {__version__}, commit `{commit}`. Read '
               '[CURRENT_RELEASE.md](CURRENT_RELEASE.md) first. The original handbook and '
               'native examples remain dated learning material, not current MCP capability promises.')
    for path in out.glob('*.md'):
        if path.name in ('SOURCE_INDEX.md','VALIDATION.md'):
            continue
        text = path.read_text()
        first, _, rest = text.partition('\n')
        if path.name == 'README.md':
            first = '# Mission-making knowledge pack '+args.pack_version
        path.write_text(first+'\n\n'+current+'\n\n'+rest.lstrip())
    guide = out/'sources/project/docs/MCP.md'
    (out/'CURRENT_RELEASE.md').write_text(f'''# Current release contract

{current}

Use the copied [integration guide](sources/project/docs/MCP.md) and
`data/recipe-schema.json` for this snapshot. Confirm the running server version
at https://sortiestarter.com/mcp/ and fetch /api/mcp-guide and the schema tool
again before remote authoring. Offline packs do not update automatically.

Syria position and saved-center checks use the published authoring envelope in
`data/map-authoring-bounds.json`; it is not certified DCS terrain/detail coverage.
Validation and generation share this check. This release adds private Admin MCP
connection diagnostics; it does not establish app connector acceptance.

Exact per-station stores, exact start speed/clock, second independent human
flight, arbitrary routes, country/flight-name overrides and custom enemy groups,
triggers/F10 menus are not MCP recipe controls yet. The original handbook covers
local PyDCS authoring beyond this remote contract. A default fallback is not a
faithful Phoenix rebuild. Historical weapons follow the selected year.

Copied project sources and generated terrain/schema inventories are refreshed.
Historical narratives, reviewed private notes and native mission examples are
preserved from pack {old['knowledge_pack_version']} / app {old['source_app_version']}.
No new historical source review or simulator flight is claimed. The old pack
remains unchanged. This remains a private handoff, not a publishable app bundle.
''')
    lines = ['# Source index','',current,'',
             '| Origin | File | Bytes | SHA-256 |','| --- | --- | ---: | --- |']
    for row in sources['sources']:
        lines.append(f"| {row['origin']} | [{row['source']}]({row['bundle']}) | {row['bytes']} | `{row['sha256']}` |")
    (out/'SOURCE_INDEX.md').write_text('\n'.join(lines)+'\n')
    (out/'VALIDATION.md').write_text('# Knowledge refresh validation\n\n'+current+
        '\n\nPrevious payloads matched their original allowlisted manifest before copying. '
        'Project source copies were refreshed and rehashed; schema, map authoring bounds '
        'and airfield/parking coverage were captured from the committed release. '
        'BUNDLE_MANIFEST.json excludes itself and records each payload. Old native '
        'examples and historical review evidence are retained, not rerun. '
        'No DCS flight or app connector acceptance is asserted.\n')
    renderer = out/'tools/render_reading_copy.py'
    renderer.write_text(renderer.read_text().replace('PACK 1.0.0', 'PACK '+args.pack_version))
    subprocess.run([sys.executable,str(renderer)],check=True)
    assert f'Guide release: **v{__version__}**' in guide.read_text()
    files = [{'path':str(p.relative_to(out)),**details(p)} for p in sorted(out.rglob('*'))
             if p.is_file() and p.name != 'BUNDLE_MANIFEST.json']
    manifest = {'schema_version':1,'knowledge_pack_version':args.pack_version,
                'source_app_version':__version__,'source_commit':commit,'created_utc':now,
                'scope':'Private agent handoff; refreshed project/MCP inventory plus explicitly dated learning material.',
                'previous_pack_version':old['knowledge_pack_version'],
                'manifest_self_excluded':True,'files':files}
    (out/'BUNDLE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob('*')):
            if path.is_file():
                z.write(path,str(Path(out.name)/path.relative_to(out)))
    print(json.dumps({'directory':str(out),'archive':str(archive),'files':len(files),
                      'app_version':__version__,'source_commit':commit}))


if __name__ == '__main__':
    main()
