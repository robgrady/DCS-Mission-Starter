"""Build a complete integration download through the existing API admission.

Downloads regenerate recipes. The version guard refuses links after an app
upgrade instead of quietly handing an integration different mission bytes.
No mission storage, caller-controlled paths or cross-machine temporary files.
"""
import hashlib
import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from missiongen import Recipe, __version__
from missiongen.share import decode_recipe, encode_recipe
from . import artifact_service
from .mission_manifest import kit_manifest, navigation_manifest

log = logging.getLogger('missionstarter.kit')
router = APIRouter()


def build_kit(recipe: Recipe, directory: Path) -> dict:
    """Build once; return paths and a JSON manifest without temporary paths."""
    recipe.validate()
    miz = directory / 'mission.miz'
    result = artifact_service.generate(recipe, str(miz), brief_dir=str(directory))
    stats = result['stats']
    navigation = navigation_manifest(stats, miz)
    files = [('mission.miz', miz, 'application/zip')]
    for key, name, mime in [('brief_pdf', 'brief.pdf', 'application/pdf'),
                            ('brief_md', 'brief.md', 'text/markdown'),
                            ('dtc_card', 'dtc_setup_card.md', 'text/markdown')]:
        if result.get(key):
            files.append((name, Path(result[key]), mime))
    manifest = {'schema_version': 1, 'app_version': __version__,
                'recipe': recipe.to_dict(), 'share_code': encode_recipe(recipe),
                'mission': {'filename': 'mission.miz', 'sha256': hashlib.sha256(miz.read_bytes()).hexdigest(),
                            'bytes': miz.stat().st_size},
                'warnings': result['warnings'], 'kit': kit_manifest(stats),
                'flight_composition': stats.get('flight_composition'),
                'readiness': result.get('readiness'),
                'files': [{'name': name, 'media_type': mime} for name, _, mime in files]}
    bundle = directory / 'mission_kit.zip'
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as out:
        for name, path, _ in files:
            out.write(path, name)
        for name, value in [('comms.json', result['communications']), ('navigation.json', navigation)]:
            out.writestr(name, json.dumps(value, ensure_ascii=False, indent=2))
            manifest['files'].append({'name': name, 'media_type': 'application/json'})
        with zipfile.ZipFile(miz) as mission:
            for name in sorted(mission.namelist()):
                if name.startswith('KNEEBOARD/IMAGES/') and name.lower().endswith('.png'):
                    page = 'kneeboard/' + Path(name).name
                    out.writestr(page, mission.read(name))
                    manifest['files'].append({'name': page, 'media_type': 'image/png'})
        out.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return {'manifest': manifest, 'miz': miz, 'bundle': bundle}


def generation_preview(recipe: Recipe) -> dict:
    """Produce actual native mission facts; delete all files even on failure."""
    with tempfile.TemporaryDirectory(prefix='sortie-mcp-') as directory:
        return build_kit(recipe, Path(directory))['manifest']


@router.get('/api/mission-kit')
def download_kit(r: str, version: str, format: Literal['kit', 'miz'] = 'kit',
                 sha256: str | None = Query(default=None, pattern=r'^[0-9a-f]{64}$')):
    """Regenerate a version-pinned mission or full kit from a share code."""
    if version != __version__:
        raise HTTPException(409, 'This download belongs to another app version. Call generate_mission again for current links.')
    if len(r) > 100_000:
        raise HTTPException(400, 'Share code is too large.')
    directory = Path(tempfile.mkdtemp(prefix='sortie-kit-'))
    try:
        try:
            recipe = decode_recipe(r)
        except Exception as exc:
            raise HTTPException(400, 'Invalid share code. Validate the recipe and generate new links.') from exc
        result = build_kit(recipe, directory)
        if sha256 and result['manifest']['mission']['sha256'] != sha256:
            raise HTTPException(409, 'Mission content changed. Call generate_mission again for current links.')
        path = result['bundle' if format == 'kit' else 'miz']
    except HTTPException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    except artifact_service.USER_ERRORS as exc:
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        log.exception('mission kit generation failed')
        raise HTTPException(500, 'Internal error generating the mission kit.')
    return FileResponse(path, filename=path.name, media_type='application/zip',
                        headers={'Cache-Control': 'no-store'},
                        background=BackgroundTask(shutil.rmtree, directory, ignore_errors=True))
