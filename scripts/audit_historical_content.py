#!/usr/bin/env python3
"""Inventory claims and affected content; source/readback inventory is not a truth verdict."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from missiongen import __version__
from missiongen.historical_library import catalog, mission_references
from missiongen.historical_world import template_previews
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe, templates


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def inventory(previous=None):
    library = catalog(); service = load_json('aircraft_service'); rows = []
    for key, template in templates().items():
        for era, maps in template_previews(key).items():
            for map_key, history in maps.items():
                recipe = effective_recipe(key, era, map_key)
                aircraft = recipe.get('aircraft', 'F_16C_50')
                # Preserve exact native type translation for known catalog classes.
                from missiongen.resolver import resolve, UnknownUnitError
                try:
                    native_type = resolve('planes.'+aircraft).id
                except (AttributeError, ImportError, ValueError, UnknownUnitError):
                    native_type = aircraft
                all_readings = catalog(map_key=map_key, on=history['date'])['entries']
                family = 'F-4' if native_type.replace('_','-').startswith('F-4') else None
                all_readings = [r for r in all_readings if not r['aircraft_families'] or family in r['aircraft_families']]
                issues = []
                window = service.get(aircraft)
                if window is None:
                    issues.append('Aircraft service window unrecorded; exact variant/operator requires research.')
                elif int(history['date'][:4]) < window[0] or window[1] and int(history['date'][:4]) > window[1]:
                    issues.append('Scenario year falls outside the recorded type service window; review adaptation/date/variant intent.')
                if not history['sources']:
                    issues.append('No authored scenario source links; historical claims need source review.')
                if not all_readings:
                    issues.append('No matching archive reading; this is a coverage gap, not proof of an incorrect mission.')
                map_units = [r for r in library['unit_records'] if r['map']==map_key]
                evidence = {'recipe':recipe,'history':history,'description':template.get('library',{}),
                    'readings':all_readings,'unit_observations':map_units,
                    'sources':{sid: library['sources'][sid] for r in all_readings+map_units for ref in r['sources'] for sid in [ref['source_id']]}}
                row_id=f'template/{key}/{era}/{map_key}'
                rows.append({'id':row_id,'kind':'live_template','template':key,'label':template['label'],
                    'map':map_key,'era':era,'scenario_date':history['date'],'aircraft':aircraft,
                    'classification':history['classification'],'source_links':history['sources'],
                    'matching_readings':[r['id'] for r in all_readings],
                    'brief_readings':[r['id'] for r in mission_references(map_key,history['date'],native_type)],
                    'unit_observations':[r['id'] for r in map_units],
                    'review_status':'awaiting_claim_review','issues':issues,'fingerprint':fingerprint(evidence)})
    for path in sorted((ROOT/'packs').glob('*.sspack')):
        with zipfile.ZipFile(path) as archive:
            manifest=json.loads(archive.read('pack.json'))
            for event in manifest['syllabus']:
                miz=event.get('files',{}).get('mission')
                if not miz:continue
                blob=archive.read(miz)
                row_id=f"pack/{manifest['id']}/{miz}"
                rows.append({'id':row_id,'kind':'published_collection_mission','pack':manifest['id'],
                    'label':event.get('label',miz),'content_version':manifest['version'],
                    'built_with':manifest['built_with'],'review_status':'awaiting_claim_and_simulator_review',
                    'fingerprint':fingerprint({'event':event,'native_sha256':hashlib.sha256(blob).hexdigest(),
                        'historical_context':manifest.get('historical_context')})})
    for key, reading in [(r['id'],r) for r in library['entries']]:
        rows.append({'id':'reading/'+key,'kind':'historical_reading',
            'review_status':'bounded_source_review; simulator_claims_not_certified',
            'fingerprint':fingerprint({'reading':reading,'sources':{ref['source_id']:library['sources'][ref['source_id']] for ref in reading['sources']}})})
    for key, profile in library['profiles'].items():
        rows.append({'id':'profile/'+key,'kind':'dated_point_profile',
            'review_status':'printed_coordinate_review; datum_and_validity_unverified',
            'fingerprint':fingerprint({'profile':profile,'source':library['sources'][profile['source']['source_id']]})})
    coverage=load_json('historical_coverage')
    for key, element in coverage['elements'].items():
        rows.append({'id':'airspace/'+key,'kind':'map_reference','evidence':element['evidence'],
                     'geometry_accuracy':element['geometry_accuracy'],
                     'review_status':'bounded_reference; operational_validity_unverified',
                     'fingerprint':fingerprint(element)})
    prior={row['id']:row for row in (previous or {}).get('records',[])}
    for row in rows:
        old=prior.get(row['id'])
        if old and 'claim_assessment' in old:
            field='claim_assessment' if old['fingerprint']==row['fingerprint'] else 'previous_claim_assessment'
            row[field]=old['claim_assessment']
        row['change_status']='new_to_ledger' if old is None else 'changed_since_review' if old['fingerprint']!=row['fingerprint'] else 'unchanged_since_snapshot'
    return {'schema_version':1,'app_version':__version__,'scope':'Review queue and dependency inventory, not independent historical certification.',
        'counts':{kind:sum(r['kind']==kind for r in rows) for kind in sorted({r['kind'] for r in rows})},
        'limitations':['No source page is newly verified by this inventory.',
            'Fingerprints identify content/evidence changes; unchanged does not mean correct.',
            'Published native archives need claim comparison and DCS flight checks.',
            'Current matching readings never certify continuous unit occupancy or livery identity.'],
        'records':rows,'removed_since_snapshot':sorted(set(prior)-{r['id'] for r in rows})}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--previous',type=Path)
    args=parser.parse_args()
    previous=json.loads(args.previous.read_text()) if args.previous else None
    result=inventory(previous)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'counts':result['counts'],'changed':sum(r['change_status']=='changed_since_review' for r in result['records']),
        'output':str(args.output)}))


if __name__=='__main__':main()
