// Click-through frame recorder for tuned boards (Playwright in Docker).
// Each scenario: draw a red ring/box (__mark / __box) on what gets clicked, screenshot, act, repeat.
// Output: $OUT/sNN-<n>.jpg; add one "sNN-<n><TAB>caption" line per frame to captions.tsv yourself.
// Env: APP (default http://host.docker.internal:3000, your app as seen from the container),
//      OUT (default /out), ONLY (comma list of scenario ids, e.g. s01),
//      TOKEN (optional login token; read only from the environment, stored in localStorage as `token`).
// The s01 block below is an example for a made-up app: copy it, rename the id, change the steps.
//
// Run it from the skill folder, with the app running on your machine:
//   mkdir -p frames
//   docker run --rm -v "$PWD":/work -e APP -e TOKEN -e OUT=/work/frames -e ONLY=s01 --add-host=host.docker.internal:host-gateway \
//     mcr.microsoft.com/playwright:v1.59.1-noble \
//     sh -c 'cd /tmp && npm i --silent playwright@1.59.1 && cp /work/scripts/record.mjs . && node record.mjs'
import { chromium } from 'playwright';
const APP = process.env.APP || 'http://host.docker.internal:3000';
const TOKEN = process.env.TOKEN;
const OUT = process.env.OUT || '/out';
const ONLY = (process.env.ONLY || '').split(',').filter(Boolean);
const log = (...a) => console.log(...a);

const helpers = () => {
  window.__unmark = () => document.querySelectorAll('.__mk').forEach(n => n.remove());
  window.__mark = (x, y, label) => {
    window.__unmark();
    const ring = document.createElement('div'); ring.className = '__mk';
    Object.assign(ring.style, { position: 'fixed', left: (x - 22) + 'px', top: (y - 22) + 'px', width: '44px', height: '44px', borderRadius: '50%', border: '3px solid #e5262a', background: 'transparent', boxShadow: '0 0 0 4px rgba(255,255,255,.7)', zIndex: 2147483647, pointerEvents: 'none' });
    const tag = document.createElement('div'); tag.className = '__mk'; tag.textContent = label;
    const left = Math.min(x + 28, innerWidth - 260);
    Object.assign(tag.style, { position: 'fixed', left: left + 'px', top: (y - 14) + 'px', maxWidth: '240px', padding: '5px 10px', borderRadius: '6px', background: '#e5262a', color: '#fff', font: '600 13px/1.3 system-ui, sans-serif', zIndex: 2147483647, pointerEvents: 'none', boxShadow: '0 2px 6px rgba(0,0,0,.25)' });
    document.body.append(ring, tag);
  };
  window.__markEl = (el, label) => { const b = el.getBoundingClientRect(); window.__mark(b.left + b.width / 2, b.top + b.height / 2, label); };
  window.__box = (el, label, where) => {
    window.__unmark();
    const b = el.getBoundingClientRect();
    const box = document.createElement('div'); box.className = '__mk';
    Object.assign(box.style, { position: 'fixed', left: (b.left - 5) + 'px', top: (b.top - 5) + 'px', width: (b.width + 10) + 'px', height: (b.height + 10) + 'px', borderRadius: '10px', border: '3px solid #e5262a', boxShadow: '0 0 0 3px rgba(255,255,255,.75)', zIndex: 2147483647, pointerEvents: 'none' });
    const cy = b.top + b.height / 2;
    const tag = document.createElement('div'); tag.className = '__mk'; tag.textContent = label;
    Object.assign(tag.style, { position: 'fixed', padding: '5px 10px', borderRadius: '6px', background: '#e5262a', color: '#fff', font: '600 13px/1.3 system-ui, sans-serif', zIndex: 2147483647, pointerEvents: 'none', boxShadow: '0 2px 6px rgba(0,0,0,.25)', whiteSpace: 'nowrap' });
    document.body.append(box, tag);
    const tw = tag.offsetWidth, th = tag.offsetHeight;
    let x, y;
    if (where === 'below' || (where !== 'above' && b.right + 14 + tw > innerWidth - 8)) { x = Math.max(8, Math.min(b.left, innerWidth - tw - 8)); y = b.bottom + 12; if (where !== 'below' && y + th > innerHeight - 8) y = b.top - th - 12; }
    else if (where === 'above') { x = Math.max(8, Math.min(b.left, innerWidth - tw - 8)); y = b.top - th - 12; }
    else { x = b.right + 14; y = cy - th / 2; }
    tag.style.left = x + 'px'; tag.style.top = y + 'px';
  };
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1200, height: 800 } });
await ctx.addInitScript(helpers);
const page = await ctx.newPage();
page.on('pageerror', e => log('pageerror', e.message.slice(0, 200)));
const shot = async (name) => { await page.waitForTimeout(250); await page.screenshot({ path: `${OUT}/${name}.jpg`, type: 'jpeg', quality: 80 }); log('shot', name); };
const unmark = () => page.evaluate(() => window.__unmark());

await page.goto(APP + '/');
if (TOKEN) await page.evaluate((t) => localStorage.setItem('token', t), TOKEN);

if (ONLY.includes('s01')) {
  await page.goto(APP + '/settings');
  await page.waitForTimeout(1000);
  await page.evaluate(() => window.__box(document.querySelector('select'), 'Pick the new setting', 'below'));
  await shot('s01-1');
  await unmark();
  await page.locator('select').selectOption({ index: 1 });
  const save = page.getByRole('button', { name: 'Save' });
  await save.evaluate((el) => window.__markEl(el, 'Then save'));
  await shot('s01-2');
  await unmark();
  await save.click();
  await page.waitForTimeout(500);
  await page.evaluate(() => window.__mark(innerWidth / 2, 120, 'The new setting shows at once'));
  await shot('s01-3');
  await unmark();
}
await browser.close();
