#!/usr/bin/env python3
"""Produce the public coverage atlas, research record and shared symbol specimen."""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from missiongen import __version__
from missiongen.historical_coverage import report
from missiongen.corridor_chart import Canvas, INK, TRANSIT, ZONE, PAPER, _hatch
from build_sources_html import STYLE


def symbols():
    cv = Canvas(1040, 650)
    cv.text((32,32),'HISTORICAL MAP SYMBOLS',26,INK,weight='bold')
    cv.text((32,65),'Shape + line pattern + label carry meaning. Existing Flightline palette.',15,INK)
    samples = [
        ('lane','Reconstructed route','Dashed lane; width and block are planning values.'),
        ('gate','Reporting gate','Diamond; ~ marks approximate placement.'),
        ('zone','Control / reference zone','Circle; radius units and source date in the label.'),
        ('restricted','Restricted / exclusion boundary','Hatched edge; legal effect comes from its dated source.'),
        ('deconfliction','Deconfliction reference','Dash-dot line; coordination permissions are not modeled.'),
        ('training','Illustrative training geometry','Dotted shape + TRAINING. No verified real boundary.'),
        ('axis','Tactical threat axis','Arrow + AXIS / TRAINING. No flight route is implied.'),
    ]
    for i,(kind,title,note) in enumerate(samples):
        y=113+i*65
        x=40;color=ZONE if kind in ('restricted','training','axis','deconfliction') else TRANSIT
        if kind=='lane': cv.polygon([(x,y-12),(x+125,y-12),(x+125,y+12),(x,y+12)],stroke=color,width=2,dash=(7,4))
        elif kind=='gate': cv.polygon([(x+60,y-19),(x+79,y),(x+60,y+19),(x+41,y)],stroke=color,width=2)
        elif kind=='zone': cv.circle((x+60,y),21,stroke=color,width=2)
        elif kind=='restricted':
            poly=[(x,y-19),(x+125,y-19),(x+125,y+19),(x,y+19)]
            cv.polygon(poly,stroke=color,width=2);_hatch(cv,poly,color,step=12,inset=6)
        elif kind=='training': cv.polygon([(x,y-18),(x+125,y-18),(x+125,y+18),(x,y+18)],stroke=color,width=2,dash=(1,5))
        elif kind=='axis':
            cv.line([(x,y),(x+104,y)],color,3)
            cv.polygon([(x+125,y),(x+102,y-12),(x+102,y+12)],fill=color)
        else:
            for offset in range(0,125,24):
                cv.line([(x+offset,y),(x+min(offset+14,125),y)],color,2)
                if offset+19<125:cv.circle((x+offset+19,y),1.2,fill=color)
        cv.text((205,y-7),title,17,INK,weight='bold')
        cv.text((205,y+16),note,14,INK)
    cv.text((32,600),'DOC = documented structure · REPORTED = reported track · TRAINING = authored exercise',14,INK,weight='bold')
    cv.text((32,626),'REF = source/event date, not ongoing validity · DATE ? = unknown · ~ = reconstructed',14,INK)
    return cv


def page(data):
    esc=html.escape;cards=[]
    status={'partial_network':'Partial routing network','tactical_only':'Tactical axes; no routing network','overlay_only':'Reference overlays; no routing network','no_drawn_geometry':'No drawn corridor or airspace geometry'}
    for row in data['map_eras']:
        findings=[]
        for f in row['research']:
            links=' · '.join(f'<a href="{esc(url,quote=True)}" rel="noopener">Source {i+1}</a>' for i,url in enumerate(f['sources']))
            findings.append(f'<details><summary>{esc(f["name"])} — {esc(f["reference_date"] or "date not established")}</summary><p>{esc(f["claim"])}</p><p><b>Still missing:</b> {esc(f["remaining_gap"])}</p><p>{links}</p><p class="sub">{esc(f["access"])}</p></details>')
        entries=[]
        for e in row['elements']:
            entries.append(f'<li><b>{esc(e["name"])}</b> · {esc(e["evidence"].replace("_"," "))}<br>{esc(e["geometry_accuracy"].replace("_"," "))} · REF {esc(e["reference_date"] or "?")} · operational validity {esc(e["valid_from"] or "?")} to {esc(e["valid_to"] or "?")}<br>{esc(e.get("source_text") or "No authenticated individual source; training design.")}</li>')
        counts=row['counts']
        cards.append(f'<article data-map="{esc(row["map"])}" data-era="{esc(row["era"])}"><h2>{esc(row["map_label"])} · {esc(row["era_label"])}</h2><p><b>{status[row["status"]]}</b><br>{counts["route_segments"]} route segments · {counts["tactical_axes"]} threat axes · {counts["overlay_features"]} overlay features</p><p>No complete historical or dated-validity certification.</p>{"".join(findings)}<p><b>Next evidence needed:</b> {esc(row["research_next"])}</p><details><summary>Audit the {len(entries)} drawn elements</summary><ul>{"".join(entries)}</ul></details></article>')
    options=lambda key,label:'<option value="">All '+label+'</option>'+''.join(f'<option value="{esc(k)}">{esc(v)}</option>' for k,v in sorted({r[key]:r[key+'_label'] for r in data['map_eras']}.items()))
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Historical map coverage — Sortie Starter</title><style>'+STYLE+'''\narticle{border-top:1px solid var(--line);padding-bottom:20px}details{font-family:var(--sans);margin:12px 0;padding:10px;background:var(--panel);border-radius:6px}summary{cursor:pointer;font-weight:650}p,li,a{overflow-wrap:anywhere}select{font:inherit;max-width:100%;padding:8px;border:1px solid var(--line);background:white;color:var(--text)}.filters{display:flex;gap:18px;flex-wrap:wrap}.symbol{width:100%;height:auto}summary:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:3px}[hidden]{display:none!important}</style></head><body><div class="aband"><b>SORTIE STARTER</b><span>v'''+__version__+'''</span></div><main class="wrap"><p><a href="/">Back to mission builder</a> · <a href="/api/sources">Sources</a> · <a href="/api/historical-coverage">JSON register</a></p><h1>Historical map coverage</h1><p>13 maps · 26 supported map/era pairs · reviewed 3 October 2026.</p><div class="north">A research register, not a claim that every historical corridor has been found. Routing networks, tactical axes and reference overlays serve different purposes. A route's presence does not certify its accuracy for your scenario date.</div><details><summary>Read the map symbols</summary><img class="symbol" src="/api/historical-symbols.png" alt="Dashed reconstructed lane; diamond gate; circular zone; hatched exclusion boundary; dash-dot deconfliction; dotted training shape; threat-axis arrow"><p><a href="/api/historical-symbols.svg">Download vector specimen</a></p></details><div class="filters"><label>Map <select id="map">'''+options('map','maps')+'''</select></label><label>Era <select id="era">'''+options('era','eras')+'''</select></label></div><p id="count" aria-live="polite">26 map/era pairs</p><div id="rows">'''+''.join(cards)+'''</div><p id="empty" hidden>No supported map/era pair matches these filters.</p></main><script>const map=document.getElementById('map'),era=document.getElementById('era');function filter(){let n=0;document.querySelectorAll('article[data-map]').forEach(row=>{row.hidden=!!((map.value&&row.dataset.map!==map.value)||(era.value&&row.dataset.era!==era.value));if(!row.hidden)n++;});document.getElementById('count').textContent=n+' map/era pairs';document.getElementById('empty').hidden=n>0;}map.addEventListener('change',filter);era.addEventListener('change',filter);const q=new URLSearchParams(location.search);map.value=q.get('map')||'';era.value=q.get('era')||'';filter();</script></body></html>'''


def research_markdown(data):
    lines=['# Historical airspace research — 3 October 2026','',f'Generated for v{__version__} from `missiongen/data/historical_coverage.json`.', '', 'This pass closes source-identification gaps, adds drawable references where geometry is supported, and records unresolved geometry and dates. No map is certified exhaustive. No new route, AI behavior, crossing permission or engagement rule is inferred from these findings.', '']
    seen=set()
    for row in data['map_eras']:
        lines += [f'## {row["map_label"]} / {row["era_label"]}', '', row['research_next'], '']
        for f in row['research']:
            lines += [f'### {f["name"]}', '', 'Reference: '+(f['reference_date'] or 'not established')+'. '+f['claim'], '', 'Remaining gap: '+f['remaining_gap'], '', 'Access: '+f['access'], '']
            lines += [f'- [Primary source {i+1}]({url})' for i,url in enumerate(f['sources'])]+['']
        if not row['research']:lines += ['No mappable source authenticated in this pass. Absence of a finding is not evidence that historical corridors did not exist.', '']
    return '\n'.join(lines)


def main():
    data=report();img=ROOT/'docs/img';img.mkdir(exist_ok=True)
    cv=symbols()
    (img/'historical_symbols.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cv.w} {cv.h}" role="img"><title>Historical map symbols</title><rect width="100%" height="100%" fill="white"/>'+cv.svg()+'</svg>\n')
    cv.pil().save(img/'historical_symbols.png')
    (ROOT/'docs/historical_coverage.html').write_text(page(data))
    (ROOT/'docs/research/HISTORICAL_AIRSPACE_RESEARCH.md').write_text(research_markdown(data))
    print('Historical coverage: 26 pairs, research record and symbol specimen')

if __name__=='__main__':main()
