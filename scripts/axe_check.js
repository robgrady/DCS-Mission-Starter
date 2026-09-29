#!/usr/bin/env node
/* WCAG regression gate — axe-core 4.13 (vendored, MPL-2.0) over the running
 * site in both modes, all primary views. Fails (exit 1) on ANY serious or
 * critical violation at WCAG 2.x A/AA. Run by tests/test_a11y.py and the
 * release preflight; base URL comes from argv[1].
 *
 * axe automates roughly a third of WCAG — this gate keeps the automatable
 * third from regressing. The manual obligations (screen-reader walkthrough,
 * cognitive review) live in docs/wcag-audit-2026-08-12.md.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = process.argv[2] || 'http://127.0.0.1:8765';
const AXE = fs.readFileSync(path.join(__dirname, '..', 'vendor', 'axe-core', 'axe.min.js'), 'utf8');

async function run(pg, label, bad) {
  await pg.evaluate(AXE);
  const r = await pg.evaluate(async () => await axe.run(document, {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] }
  }));
  for (const v of r.violations) {
    if (v.impact === 'serious' || v.impact === 'critical') {
      bad.push(`${label}: [${v.impact}] ${v.id} ×${v.nodes.length} — ${v.help}` +
               `\n    e.g. ${v.nodes[0].target.join(' ')}`);
    }
  }
}

(async () => {
  const b = await chromium.launch({
    executablePath: process.env.CHROMIUM || '/opt/pw-browsers/chromium' });
  const pg = await b.newPage({ viewport: { width: 1440, height: 1000 } });
  const bad = [];
  await pg.goto(BASE + '/', { waitUntil: 'networkidle' });
  await pg.waitForTimeout(600);
  await run(pg, 'entry', bad);
  for (const view of ['quick', 'library', 'builder']) {
    await pg.evaluate(v => showView(v), view);
    await pg.waitForTimeout(600);
    await run(pg, view, bad);
  }
  // the detail dialog, then night mode over the library
  await pg.evaluate(() => showView('library'));
  await pg.waitForTimeout(500);
  await pg.evaluate(() => { const c = document.querySelector('.libcard'); if (c) c.click(); });
  await pg.waitForTimeout(500);
  await run(pg, 'detail-dialog', bad);
  await pg.evaluate(() => { const x = document.querySelector('.dclose'); if (x) x.click(); });
  // the contact form (v1.64.0) — a form is the densest a11y surface we ship
  await pg.evaluate(() => openContact());
  await pg.waitForTimeout(700);
  await run(pg, 'contact-dialog', bad);
  await pg.evaluate(() => closeContact());
  await pg.evaluate(() => flipMode());
  await pg.waitForTimeout(400);
  await run(pg, 'library-night', bad);
  await pg.evaluate(() => showView('builder'));
  await pg.waitForTimeout(500);
  await run(pg, 'builder-night', bad);
  await b.close();
  if (bad.length) {
    console.error('AXE GATE FAILED — serious/critical WCAG violations:');
    for (const line of bad) console.error('  ' + line);
    process.exit(1);
  }
  console.log('axe gate: clean (8 view/mode passes, 0 serious/critical)');
})().catch(e => { console.error(e); process.exit(1); });
