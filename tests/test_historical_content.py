"""Dated source corrections must reach the catalog AND serialized mission kit."""
from datetime import date
from pathlib import Path
import zipfile
import pytest
from missiongen import Recipe, generate
from missiongen.historical_world import preview, scenario_date, snapshot, template_previews
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe
from missiongen import loadouts
from scripts.audit_library import inspect_archive

DATES = [('sinai','coldwar',None,'1973-10-06'),
         ('sinai','coldwar','proud_phantom','1980-07-10'),
         ('falklands','coldwar',None,'1982-05-21'),
         ('kola','modern',None,'2024-06-21'),
         ('afghanistan','gwot',None,'2011-06-21'),
         ('syria','modern',None,'2018-02-07'),
         ('iraq','coldwar',None,'1984-06-21')]

@pytest.mark.parametrize('mk,era,lineup,day',DATES)
def test_authored_dates_survive_native_serialization_and_document_facts(mk,era,lineup,day,tmp_path):
    r=Recipe(map=mk,era=era,lineup=lineup,aircraft='F_4E_45MC' if era=='coldwar' else 'F_16C_50',
             bb_dressing=False,bb_ambient=False,bb_sams=False,bb_awacs=False,
             bb_tanker=False,bb_kneeboard=False,seed=19)
    result=generate(r,str(tmp_path/'dated.miz'))
    facts=inspect_archive(tmp_path/'dated.miz')
    y,m,d=map(int,day.split('-'))
    assert facts['date']=={'Year':y,'Month':m,'Day':d}
    assert result['stats']['historical_context']['date']==preview(mk,era,lineup=lineup)['date']==day
    assert day in '\n'.join(facts['embedded_text'].values())
    for g in facts['groups']:
        if g['kind']!='plane': continue
        for u in g['units']:
            for p in (u.get('payload') or {}).get('pylons',{}).values():
                clsid=p.get('CLSID'); win=loadouts.window_for(clsid)
                assert not win or (win[0] or 0)<=y<=(win[1] or 9999), (u['type'],clsid,win,y)


def test_white_knights_dates_use_selected_map_and_lineup():
    t=load_json('mission_templates')
    for k,v in t.items():
        if not isinstance(v,dict) or v.get('track',{}).get('id') not in ('wk_checkout','wk_proud_phantom'):continue
        contexts=template_previews(k)['coldwar']
        for mk,h in contexts.items():
            assert h['date']==('1980-07-10' if mk=='sinai' else '1980-06-21'),(k,mk,h)
    assert preview('kola','modern')['classification']=='fictional_exercise'


def test_known_future_stores_are_replaced_only_on_legal_dcs_stations():
    from dcs.planes import F_4E_45MC
    station=next(p for p in F_4E_45MC.pylons if any('AIM-7M' in n for n in loadouts._pylon_stores(F_4E_45MC,p).values()))
    late=next(c for c,n in loadouts._pylon_stores(F_4E_45MC,station).items() if 'AIM-7M' in n)
    assert not loadouts._era_ok(late,'coldwar',1978)
    fit=loadouts.dated_fit({'pylons':{str(station):late}},F_4E_45MC.id,1978)
    replacement=fit['pylons'][str(station)]
    assert replacement!=late
    assert replacement in loadouts._pylon_stores(F_4E_45MC,station)
    assert loadouts.store_class(replacement)==loadouts.store_class(late)
    assert loadouts._era_ok(replacement,'coldwar',1978)
    assert '1978' in fit['label']
    unknown='{UNRECORDED-STORE}'
    assert loadouts.dated_fit({'pylons':{'1':unknown}},F_4E_45MC.id,1978)['pylons']['1']==unknown


def test_context_is_in_pdf_markdown_and_kneeboard_with_actual_dtg(tmp_path):
    from pypdf import PdfReader
    from missiongen.builder import StarterBuilder
    from missiongen.brief import _dtg
    from missiongen.kneeboard import pages_text
    r=Recipe(map='sinai',era='coldwar',lineup='proud_phantom',aircraft='F_4E_45MC',
             bb_dressing=False,bb_ambient=False,bb_sams=False,bb_awacs=False,bb_tanker=False)
    b=StarterBuilder(r);b.build()
    assert _dtg(b.brief_ctx)=='101200L JUL 1980'
    result=generate(r,str(tmp_path/'pp.miz'),str(tmp_path))
    md=Path(result['brief_md']).read_text()
    assert '1980-07-10' in md and 'advance parties' in md and 'uncertified' in md
    z=zipfile.ZipFile(tmp_path/'pp.miz')
    assert len([n for n in z.namelist() if n.startswith('KNEEBOARD/')])>=5
    assert any('HISTORICAL CONTEXT' in n for n in b.kb_ctx['historical_notes'])
    pdf=PdfReader(result['brief_pdf'])
    assert len(pdf.pages)>=5
    assert pdf.metadata.creation_date.date()==date(1980,7,10)


def test_overlay_geometry_is_retained_but_claims_and_source_dates_are_qualified():
    a=load_json('historical_airspace')
    n=a['nevada']['groom_box']
    assert n['source_effective_date']=='1995-07-20'
    assert len(n['features'][0]['corners'])==14
    assert n['features'][0]['corners'][0]==[36.683333,-115.934167]
    assert '20625' in n['features'][0]['source'] and '20661' not in n['features'][0]['source']
    assert 'bounding circle' in ' '.join(n['brief'])
    b=a['germany']['berlin_corridors'];text=' '.join(b['brief'])
    assert 'exercise limit' in text and 'conditional fighter escort' in text
    assert '13,000' not in text
    assert all(f['width_sm']==20 for f in b['features'] if f['kind']=='corridor')
    e=a['syria']['euphrates_deconfliction']
    assert e['attested_on']=='2018-02-07' and 'valid_from' not in e
    assert 'did not establish' in ' '.join(e['brief'])
    af=a['afghanistan']['oef_airspace_control']
    assert af['geometry_accuracy']=='illustrative'
    assert af['vertical_limits'] is None and af['controlling_agency'] is None


def test_base_roles_do_not_conflate_host_operator_and_coalition():
    maps=load_json('maps')
    s=snapshot('germany','coldwar',date(1978,6,21),maps['germany']['presets']['coldwar'])
    p=next(b for b in s.bases if b.name=='Parchim')
    assert (p.territorial_host,p.military_operator,p.display_nation,p.mission_coalition)==('GDR','USSR','USSR','red')
    s=snapshot('afghanistan','gwot',date(2011,6,21),maps['afghanistan']['presets']['gwot'])
    p=next(b for b in s.bases if b.name=='Camp Bastion')
    assert (p.territorial_host,p.military_operator,p.display_nation)==('Afghanistan','UK','UK')
    assert all(b.military_operator is None for b in snapshot('caucasus','coldwar',date(1978,6,21),maps['caucasus']['presets']['coldwar']).bases)


def test_reversed_or_out_of_era_authored_dates_are_rejected():
    with pytest.raises(ValueError,match='outside its era'):
        scenario_date({'scenario_date':'2024-06-21'},load_json('eras')['coldwar'])


def test_long_source_urls_fit_the_document_columns_without_losing_characters():
    from PIL import Image, ImageDraw
    from missiongen import brief, kneeboard
    source=load_json('theater_identity')['germany']['coldwar']['identities']['Parchim']['sources'][0]
    for renderer in (brief,kneeboard):
        d=ImageDraw.Draw(Image.new('RGB',(renderer.W,renderer.H)))
        font=renderer._fonts()['small']
        width=renderer.W-120
        lines=renderer._wrap(d,font,source,width)
        assert ''.join(lines)==source
        assert all(d.textlength(line,font=font)<=width for line in lines)
