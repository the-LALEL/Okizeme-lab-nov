// Opens the built page at a phone-sized viewport in light and dark, checks that it
// renders the card with no sideways scroll and no script errors, and saves screenshots.
// Usage: node tests/card_smoke.js <screenshot_dir>
const path = require('path');
const { chromium } = require('playwright');

(async () => {
  const outDir = process.argv[2] || '.';
  const page_url = 'file://' + path.resolve(__dirname, '..', 'site', 'index.html');
  const browser = await chromium.launch();
  const failures = [];
  for (const scheme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: scheme, deviceScaleFactor: 1 });
    const page = await ctx.newPage();
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto(page_url, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#tiers .tier');
    const facts = await page.evaluate(() => ({
      ender: document.getElementById('ender').textContent,
      kd: document.getElementById('kd').textContent,
      tiers: document.querySelectorAll('#tiers .tier').length,
      firstBlock: document.querySelector('#tiers .tier .block').textContent,
      firstSteps: Array.from(document.querySelectorAll('#tiers .tier')[0].querySelectorAll('.step')).map(n => n.firstChild.textContent),
      rows: document.querySelectorAll('#rows li').length,
      sideways: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      bg: getComputedStyle(document.body).backgroundColor,
    }));
    if (errors.length) failures.push(`${scheme}: script errors ${errors.join(' | ')}`);
    if (facts.ender !== 'LK Tatsu') failures.push(`${scheme}: ender ${facts.ender}`);
    if (facts.kd !== 'Knockdown +35') failures.push(`${scheme}: kd ${facts.kd}`);
    if (facts.tiers !== 4) failures.push(`${scheme}: tiers ${facts.tiers}`);
    if (facts.firstBlock !== '+4') failures.push(`${scheme}: first block ${facts.firstBlock}`);
    if (facts.firstSteps.join('>') !== 'whiff 5LP>6HP') failures.push(`${scheme}: first steps ${facts.firstSteps.join('>')}`);
    if (facts.rows !== 22) failures.push(`${scheme}: rows ${facts.rows}`);
    if (facts.sideways > 0) failures.push(`${scheme}: page scrolls sideways by ${facts.sideways}px`);
    await page.screenshot({ path: path.join(outDir, `card-${scheme}.png`), fullPage: true });
    await page.click('details.all summary');
    await page.screenshot({ path: path.join(outDir, `card-${scheme}-all.png`), fullPage: true });
    const after = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (after > 0) failures.push(`${scheme}: full list scrolls sideways by ${after}px`);
    console.log(scheme, JSON.stringify(facts));
    await ctx.close();
  }
  await browser.close();
  if (failures.length) { console.error('FAIL\n' + failures.join('\n')); process.exit(1); }
  console.log('OK: card renders at 390x844 in light and dark, no sideways scroll, no script errors');
})();
