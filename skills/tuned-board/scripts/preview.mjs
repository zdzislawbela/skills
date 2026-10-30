// Renders a built board outside claude.ai: laptop 1280x800 and phone 390x844, light and dark.
// The page sees a stand-in for window.claude that serves the seed from build.py --seed-files, so
// sign-offs, notes and messages show; nothing is saved.
//   node preview.mjs PAGE.html SEED_DIR OUT_DIR
// In Docker, from the skill folder, for the example board:
//   mkdir -p .preview/seed
//   python3 scripts/build.py examples/template-board.json --out .preview/page.html --seed .preview/seed.json --seed-files .preview/seed --embed-missing
//   docker run --rm -v "$PWD":/work mcr.microsoft.com/playwright:v1.59.1-noble \
//     sh -c 'cd /tmp && npm i --silent playwright@1.59.1 && cp /work/scripts/preview.mjs . && node preview.mjs /work/.preview/page.html /work/.preview/seed /work/.preview/shots'
import { mkdirSync, readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { chromium } from 'playwright';

const [page_, seedDir, outDir] = process.argv.slice(2);
if (!outDir) { console.error('usage: preview.mjs PAGE.html SEED_DIR OUT_DIR'); process.exit(1); }
mkdirSync(outDir, { recursive: true });

const collections = { items: [], messages: [] };
for (const f of readdirSync(seedDir)) {
  const m = f.match(/^(items|messages)\.(.+)\.json$/);
  if (m) collections[m[1]].push({ id: m[2], data: JSON.parse(readFileSync(join(seedDir, f), 'utf8')) });
}

const stub = (seed) => {
  const snapOf = (name) => ({ docs: seed[name].map((d) => ({ id: d.id, data: () => d.data })) });
  const collection = (name) => ({
    onSnapshot(next) { next(snapOf(name)); return () => {}; },
    doc: (id) => ({ set: async () => {}, update: async () => {}, delete: async () => {}, id }),
    add: async () => ({ id: 'new' }),
  });
  const db = { collection };
  const user = { id: async () => 'preview', can: async () => true, profiles: async (ids) => Object.fromEntries(ids.map((i) => [i, { name: i }])) };
  window.claude = { use: async (what) => (what === 'db' ? db : what === 'user' ? user : null) };
};

const browser = await chromium.launch();
for (const [dev, viewport] of [['laptop', { width: 1280, height: 800 }], ['phone', { width: 390, height: 844 }]]) {
  for (const colorScheme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport, colorScheme });
    await ctx.addInitScript(stub, collections);
    const page = await ctx.newPage();
    page.on('pageerror', (e) => console.log('pageerror', e.message.slice(0, 200)));
    await page.goto('file://' + resolve(page_), { waitUntil: 'load' });
    await page.waitForTimeout(800);
    const sideways = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    await page.screenshot({ path: join(outDir, `${dev}-${colorScheme}.png`) });
    // The first card open: the part of a board people read most.
    await page.locator('.tile button[aria-expanded]').first().click();
    await page.waitForTimeout(300);
    await page.locator('.tile').first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: join(outDir, `${dev}-${colorScheme}-card.png`) });
    console.log(dev, colorScheme, 'sideways scroll px:', sideways);
    await ctx.close();
  }
}
await browser.close();
