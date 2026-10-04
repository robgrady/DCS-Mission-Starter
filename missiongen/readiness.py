"""Selection checks and emitted flight facts; never certify a simulator flight."""
from . import __version__
from .builder import StarterBuilder, prepare_world, EraViolation
from .resolver import load_json
from .dressing import _measured_slot_heading


def selection_report(recipe, builder=None, context=None):
    recipe.validate()
    builder = builder or StarterBuilder(recipe)
    ctx = context or prepare_world(builder)
    aircraft_key = recipe.aircraft
    if recipe.template in ('backseat_izlid','backseat_intercept'):
        aircraft_key = 'F_14B_U'
    elif recipe.template == 'rio_fleet_defense':
        aircraft_key = 'F_14A_135_GR' if recipe.era == 'coldwar' else 'F_14B'
    aircraft = builder._resolve_aircraft(aircraft_key)
    requirements = [{'kind': 'map', 'key': recipe.map, 'label': ctx.map_cfg['label'],
                     'free': ctx.map_cfg.get('free', False)},
                    {'kind': 'aircraft', 'key': aircraft_key, 'label': aircraft.id,
                     'free': aircraft_key in ('TF_51D', 'Su_25T')}]
    notes = list(builder.warnings)
    hull = None
    if ctx.bb_carrier:
        if recipe.coalition != 'blue':
            if ctx.carrier_home:
                raise EraViolation('Carrier home requires the blue coalition. Choose a friendly airfield or blue coalition.')
            notes.append('Carrier support is blue-only and will be skipped.')
        else:
            hull = recipe.carrier_hull or {'wwii':'essex','coldwar':'forrestal','modern':'stennis','gwot':'stennis'}[recipe.era]
            from missiongen.deck import _load_hull
            data = _load_hull(hull)
            if 'carrier' not in ctx.map_cfg:
                if ctx.carrier_home:
                    raise EraViolation('This map has no carrier location. Choose a coastal map or a friendly airfield.')
                notes.append('This map has no carrier location; carrier support will be skipped.')
            if ctx.carrier_home:
                builder._check_carrier_capable(recipe.aircraft, aircraft, hull)
            if data.get('module') and 'carrier' in ctx.map_cfg:
                requirement = {'kind':'module', 'key':data['module'], 'label':data['module'], 'free':False}
                if data['module'] == 'F-14 Tomcat':
                    requirement['ownership'] = {'aircraft':'F_14B'}
                elif data['module'] == 'South Atlantic':
                    requirement['ownership'] = {'map':'falklands'}
                requirements.append(requirement)
            if recipe.cq_ride and not any(r['key']=='Supercarrier' for r in requirements):
                requirements.append({'kind':'module','key':'Supercarrier','label':'Supercarrier','free':False})
    home = ctx.home
    parking = {'home':home.name, 'status':'not_applicable', 'text':'Airborne start; no departure stand needed.'}
    if ctx.carrier_home:
        parking.update(home='CARRIER', text='Carrier deck allocation is checked during generation; no airfield heading survey applies.')
        if recipe.carrier_layout == 'packed':
            notes.append('Packed deck is a no-fly spotting layout. Select Launch or Recovery for flight operations.')
    elif recipe.start != 'air' and not ctx.crew_ops:
        fits = home.free_parking_slots(aircraft)
        all_slots = home.parking_slots
        heading_data = load_json('parking_headings').get(recipe.map, {}).get(home.name)
        measured = sum(_measured_slot_heading(heading_data, s) is not None for s in all_slots)
        parking.update(status='preview', fitting_stands=len(fits), total_stands=len(all_slots),
                       measured_directions=measured,
                       text=f'{len(fits)} size-compatible stands before allocation. Static directions: {measured}/{len(all_slots)} stand-specific measurements; other stands use field defaults or geometric estimates.')
        if len(fits) < recipe.slots:
            notes.append('Requested flight exceeds this field’s available fitting stands. Generation may relocate it to another friendly field; check the resulting warning.')
    elif ctx.crew_ops:
        parking['text'] = 'Authored crew flight; start position and allocation are determined during generation.'
    human = recipe.slots - recipe.veteran_wingmen
    flight = {'human_aircraft':human, 'ai_aircraft':recipe.veteran_wingmen,
              'text':f'{human} human aircraft + {recipe.veteran_wingmen} veteran AI wingmen (High skill). ' + ('Single-player.' if human==1 else 'Multiplayer clients.')}
    if ctx.crew_ops or recipe.formation or (load_json('mission_templates').get(recipe.template) or {}).get('wk_ride'):
        flight = {'text':'Authored flight; actual human and AI aircraft are reported after generation.'}
    return {'schema_version':1, 'app_version':__version__, 'stage':'selection',
            'requirements':requirements, 'flight':flight, 'parking':parking,
            'crew': 'Aircraft counts exclude cockpit crew positions. Consult the authored briefing and module for crew-seat and multiplayer join settings.',
            'dependencies': 'AI/support assets and installed module versions are not fully certified; inspect the generated briefing and DCS load warnings.',
            'equipment': 'Stores are composed during generation; check Your loadout in the Mission Kit.',
            'validation':{'selection':'checked', 'generated_file':'not_built', 'dcs_flight':'unverified',
                          'dcs_version':None, 'module_versions':None}, 'warnings':notes}


def generated_report(recipe, builder):
    from dataclasses import replace
    context = replace(builder.context, home=builder.phases[1].home)
    report = selection_report(recipe, builder, context)
    report['parking']['text'] = report['parking']['text'].replace('before allocation', 'remaining after allocation')
    from dcs.unit import Skill
    groups = [g for side in builder.context.mission.coalition.values()
              for country in side.countries.values()
              for kind in ('plane_group','helicopter_group') for g in getattr(country,kind,[])
              if any(u.skill in (Skill.Player,Skill.Client) for u in g.units)]
    humans = sum(u.skill in (Skill.Player,Skill.Client) for g in groups for u in g.units)
    ai = sum(u.skill not in (Skill.Player,Skill.Client) for g in groups for u in g.units)
    report['flight'] = {'human_aircraft':humans, 'ai_aircraft':ai,
                        'text':f'{humans} human aircraft + {ai} AI aircraft in the player flight. ' + ('Single-player.' if humans==1 else 'Multiplayer clients.')}
    report['stage'] = 'generated'
    report['validation']['generated_file'] = 'generated'
    report['equipment'] = builder.stats.get('player_loadout') or 'Consult the authored mission briefing for stores.'
    report['warnings'] = list(builder.warnings)
    report['parking']['home'] = 'CARRIER' if builder.context.carrier_home else builder.phases[1].home.name
    return report
