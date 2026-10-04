#!/usr/bin/env python3
"""Build the public reference shelf from the same provenance data used by APIs and missions."""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from missiongen.historical_library import catalog
from missiongen.resolver import load_json
from missiongen.historical_reference_chart import render_svg
from build_sources_html import STYLE


def build():
    data = catalog()
    esc = html.escape
    def cite(ref):
        source = data['sources'][ref['source_id']]
        pages = ', '.join(str(p) for p in ref['pdf_pages'])
        publication = source.get('publication_date') or 'not established'
        publication = f'Publication date: {publication} ({source.get("publication_date_precision") or "unknown precision"}). '
        return f'<p class="source"><b>{esc(source["title"])}</b> - PDF pages {pages}.<br>{esc(publication)}Edition SHA-256: <code>{source["sha256"]}</code><br>{esc(source["access"])}</p>'
    cards=[]
    for row in data['entries']:
        sources = ''.join(cite(ref) for ref in row['sources'])
        links = ''.join(f'<p><a href="{esc(url)}" target="_blank" rel="noopener">Official corroborating record</a></p>' for url in row['corroboration_urls'])
        cards.append(f'<article class="reference-card" id="{row["id"]}" data-map="{esc(" ".join(row["maps"]))}" data-period="{row["period"]}" data-topic="{row["topic"]}">' +
            f'<div class="eyebrow">{esc(data["topics"][row["topic"]])} · Reference reading</div><h2>{esc(row["title"])}</h2>' +
            f'<p class="period">{esc(data["periods"][row["period"]]["label"])}</p>' +
            '<ul>'+''.join(f'<li>{esc(f)}</li>' for f in row['facts'])+'</ul>' +
            '<details><summary>Sources and historical limits</summary>'+sources+links+
            '<ul>'+''.join(f'<li>{esc(f)}</li>' for f in row['limits'])+'</ul>' +
            f'<p>{esc(row["simulation_support"])}</p></details></article>')
    map_labels=load_json('maps')
    used_maps=sorted({m for row in data['entries'] for m in row['maps']}, key=lambda m:map_labels[m]['label'])
    def select(id,label,options,default):
        return f'<label for="{id}">{label}<select id="{id}"><option value="">{default}</option>'+''.join(f'<option value="{esc(k)}">{esc(v)}</option>' for k,v in options)+'</select></label>'
    filters=select('history-map','Map',[(m,map_labels[m]['label']) for m in used_maps],'All maps')
    filters+=select('history-period','Reference period',[(k,v['label']) for k,v in data['periods'].items()],'All periods')
    filters+=select('history-topic','Topic',data['topics'].items(),'All topics')
    profiles=[]
    for pid,p in data['profiles'].items():
        diagrams=''.join(f'<div class="point-diagram" data-view="{view}"'+(' hidden' if view=='local' else '')+'>'+render_svg(pid,view)+'</div>' for view in (['overview','local'] if pid=='nevada-1981' else ['overview']))
        table='<div class="table-scroll"><table><caption>Published point rows; source datum unverified</caption><thead><tr><th>No.</th><th>Point</th><th>North latitude</th><th>West longitude</th><th>Source / reference</th></tr></thead><tbody>'
        for i,point in enumerate(p['points'],1):
            reference=point.get('radial_dme_raw') or f"{point['ident']} Ch {point['channel_number']} (band unknown)"
            table+=f'<tr data-point="{esc(point["id"])}"><td>{i}</td><td>{esc(point["name"])}</td><td>{point["coordinate_raw"]["north_lat"]}</td><td>{point["coordinate_raw"]["west_lon"]}</td><td>{esc(reference)} · PDF p. {point["source"]["pdf_pages"][0]}</td></tr>'
        table+='</tbody></table></div>'
        notes=''.join(cite(ref) for ref in [p['source']])
        if p.get('procedure_candidates'):
            notes+='<h3>Procedure references</h3>' + ''.join(f'<p><b>{esc(row["name"])}</b>: {esc(row["description"])}. PDF p. {row["source"]["pdf_pages"][0]}.</p>' for row in p['procedure_candidates'])
        if p.get('refueling_reference_rows'):
            notes+='<h3>Tanker reference rows - schematic track geometry</h3><div class="table-scroll"><table><thead><tr><th>Track</th><th>Entry reference</th><th>Entry coordinate</th><th>Printed level</th></tr></thead><tbody>'
            notes+=''.join(f'<tr><td>{esc(row["track_name"])}</td><td>{esc(row["entry_radial_dme_raw"] or "Not supplied")}</td><td>{esc(row["entry_coordinate_raw"])}</td><td>{esc(row["level_raw"])}</td></tr>' for row in p['refueling_reference_rows'])+'</tbody></table></div><p>Retain the printed mixed level notation; a pressure basis has not been established for every row. No closed tanker track is reconstructed here.</p>'
        if p.get('conditions'):
            notes+='<h3>Activation and weather conditions</h3>'
            for condition in p['conditions']:
                notes+=f'<p><b>{esc(condition["element"])}</b> - '+esc(' '.join(str(v) for k,v in condition.items() if k in ('condition','request','reopen','altitude_raw','weather')))+f'. PDF p. {condition["source"]["pdf_pages"][0]}.</p>'
        profiles.append(f'<section class="reference-profile" data-profile="{pid}"'+(' hidden' if pid=='nevada-2014' else '')+f'><h3>{esc(p["label"])}</h3><p>{esc(p["plotting_note"])}</p>'+diagrams+table+'<details><summary>Procedure notes and sources</summary>'+notes+'</details></section>')
    units=[]
    for row in data['unit_records']:
        prefix='circa ' if row['date_precision']=='circa' else ''
        units.append(f'<tr data-map="{esc(row.get("map") or "off-map")}" data-event="{row["event_date"]}" data-precision="{row["date_precision"]}"><td>{prefix}{row["event_date"]}</td><td>{esc(row["unit"] or "Unit not established")}</td><td>{esc(row["base"])}</td><td>{esc(row["title"])}</td><td>{esc(", ".join(row["aircraft_variants"]))}<br>{esc(" ".join(row["notes"]))}'+'<details><summary>Source</summary>'+''.join(cite(s) for s in row['sources'])+'</details></td><td class="date-relation">Select a date to compare</td></tr>')
    holds=''.join(f'<li><b>{esc(row["title"])}</b>: {esc(row["reason"])}</li>' for row in data['source_assessments'])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Historical Library - DCS Sortie Starter</title><style>{STYLE}
    .wrap{{max-width:1180px}}body{{font-family:var(--sans)}}.reference-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}.reference-card{{border:1px solid var(--line);border-radius:10px;padding:20px;scroll-margin-top:20px}}.reference-card h2{{font-size:23px;text-transform:none;border:0;margin:6px 0;line-height:1.2;display:block}}.reference-card h2::after{{display:none}}.reference-card li{{border:0;padding:0;margin:10px 0;background:none}}.eyebrow{{font:12px var(--mono);color:var(--accent)}}.period{{font-size:13px}}.filters{{display:flex;flex-wrap:wrap;gap:14px;margin:24px 0}}label{{font-size:13px;display:flex;flex-direction:column;gap:4px}}input,select,button{{font:14px var(--sans);color:var(--text);background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:10px}}input[type=search]{{width:100%;max-width:620px}}button,summary{{cursor:pointer}}summary{{font-weight:600;color:var(--accent);padding:8px 0}}:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.source{{font-size:13px;overflow-wrap:anywhere}}code{{font:11px var(--mono);overflow-wrap:anywhere}}.table-scroll{{overflow-x:auto;max-width:100%}}table{{min-width:650px}}caption{{text-align:left;padding:8px;font-weight:600}}.point-diagram svg{{width:100%;height:auto}}.reference-point:focus,.reference-point.selected{{outline:0;filter:drop-shadow(0 0 3px #B45309)}}tr.selected td{{background:#F4F6F8;font-weight:600}}[hidden]{{display:none!important}}nav{{display:flex;gap:18px;flex-wrap:wrap;margin:14px 0}}.chart-controls{{display:flex;gap:12px;flex-wrap:wrap}}.unit-table{{min-width:920px}}.count{{font-weight:600}}@media(max-width:650px){{.reference-grid{{grid-template-columns:1fr}}.wrap{{padding:28px 16px}}h1{{font-size:36px}}.filters label{{width:100%}}.reference-card{{padding:16px}}}}
    </style><script src="/assets/historical-library.js" defer></script></head><body><div class="aband"><b>DCS Sortie Starter</b><span>v{data['app_version']}</span></div><main class="wrap"><a href="/#library">← Back to Library</a><h1>Historical <span>Library</span></h1><p class="sub">Dated records, unit timelines and period reference charts. Reviewed {data['reviewed_on']}.</p><nav aria-label="Historical library sections"><a href="#readings">Reference readings</a><a href="#nevada-charts">Dated Nevada charts</a><a href="#unit-timelines">Unit timelines</a><a href="/api/historical-coverage/report">Map coverage and symbols</a></nav><p class="north">Choose a map, period or topic to explore the sources. Reference dates identify the material being studied; they do not certify operational clearance or continuous unit presence. These readings and charts do not generate missions or change Builder selections.</p><section id="readings"><h2>Reference readings</h2><label for="history-search">Search historical references<input id="history-search" type="search" placeholder="Unit, aircraft, base, campaign or procedure…"></label><div class="filters">{filters}<button id="history-reset" type="button">Clear filters</button></div><p id="history-count" class="count" role="status" aria-live="polite">18 reference readings</p><p id="history-empty" hidden>No references match these filters. Clear a filter or search another term.</p><div class="reference-grid">{''.join(cards)}</div></section><section id="nevada-charts"><h2>Dated Nevada charts</h2><p>Each edition stays separate from the current mission-routing network. Select a marker to find its original coordinate row. Coordinates are degrees and decimal minutes.</p><div class="chart-controls"><label for="history-profile">Reference edition<select id="history-profile"><option value="nevada-1981">February 1981</option><option value="nevada-2014">2014</option></select></label><label id="history-extent-label" for="history-extent">Chart extent<select id="history-extent"><option value="overview">Overview</option><option value="local">Near Nellis</option></select></label></div><p id="history-point-detail" role="status" aria-live="polite">Select a point for its coordinate row.</p>{''.join(profiles)}<p>Download the selected edition’s <a id="history-chart-download" href="/api/historical-library/profiles/nevada-1981/chart.svg" download>SVG chart</a> or <a id="history-profile-download" href="/api/historical-library/profiles/nevada-1981">source-linked JSON data</a>.</p></section><section id="unit-timelines"><h2>Unit, base and aircraft timelines</h2><p>A group movement, squadron station event, aircraft transition and monthly strength snapshot establish different facts. The table preserves that distinction; no continuous occupancy or livery assignment is inferred.</p><label for="history-on">Compare events with this date<input id="history-on" type="date"></label><div class="table-scroll"><table class="unit-table"><thead><tr><th>Recorded date</th><th>Unit</th><th>Base / ship</th><th>Observation</th><th>Aircraft and limits</th><th>Date comparison</th></tr></thead><tbody>{''.join(units)}</tbody></table></div></section><details id="source-assessments"><summary>Sources held or excluded from historical claims</summary><ul>{holds}</ul></details><p class="rule">The archive was inventoried and selected documents were reviewed. This library does not claim exhaustive historical coverage. Flight verification in DCS remains separate from source and geometry checks.</p></main></body></html>'''


if __name__ == '__main__':
    target = ROOT / 'docs' / 'historical_library.html'
    target.write_text(build())
    print(target)
