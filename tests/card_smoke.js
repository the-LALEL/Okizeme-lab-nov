// Opens the built page at a phone-sized viewport in light and dark, walks the picker
// (default card, a typed knockdown number, a number with no answer, a knockdown range and
// its per-value link), and fails on any sideways scroll or script error. Saves screenshots.
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
    const expect = (ok, what) => { if (!ok) failures.push(`${scheme}: ${what}`); };
    const sideways = () => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    const text = sel => page.evaluate(s => { const n = document.querySelector(s); return n ? n.textContent : null; }, sel);
    const count = sel => page.evaluate(s => document.querySelectorAll(s).length, sel);

    await page.goto(page_url, { waitUntil: 'domcontentloaded' });
    await page.waitForSelector('#tiers .tier');
    expect(await text('#ender') === 'LK Tatsu', `default ender ${await text('#ender')}`);
    expect(await text('#kd') === 'Knockdown +35', `default kd ${await text('#kd')}`);
    expect(await count('#tiers .tier') === 4, 'default card should have 4 Drive tiers');
    expect(await text('#tiers .tier .block') === '+4', `first block ${await text('#tiers .tier .block')}`);
    expect(await text('#all-summary') === 'All 22 timings', `summary ${await text('#all-summary')}`);
    expect(await count('#pick-ender option') === 41, `picker options ${await count('#pick-ender option')}`);
    expect(await sideways() <= 0, 'default card scrolls sideways');
    await page.screenshot({ path: path.join(outDir, `card-${scheme}.png`), fullPage: true });

    await page.fill('#pick-k', '44');
    expect(await text('#ender') === 'Knockdown +44', `typed 44 gave ${await text('#ender')}`);
    expect(await count('#tiers .tier') >= 1, 'knockdown +44 should have picks');
    expect(await sideways() <= 0, 'number card scrolls sideways');
    await page.screenshot({ path: path.join(outDir, `number-${scheme}.png`), fullPage: true });

    await page.fill('#pick-k', '2');
    expect(await text('#ender') === 'Knockdown +2', `typed 2 gave ${await text('#ender')}`);
    expect(await count('#tiers .none') === 1 && await count('#tiers .tier') === 0, 'knockdown +2 should say there is no qualifying strike');

    await page.selectOption('#pick-ender', 'mk-high-blade-kick');
    expect(await text('#kd') === 'Knockdown +40 to +46', `range kd ${await text('#kd')}`);
    expect(await count('#per-kd-list a') === 7, `range should list 7 exact values, got ${await count('#per-kd-list a')}`);
    expect(await sideways() <= 0, 'range card scrolls sideways');
    await page.screenshot({ path: path.join(outDir, `range-${scheme}.png`), fullPage: true });
    await page.click('#per-kd-list a');
    await page.waitForFunction(() => document.getElementById('ender').textContent === 'Knockdown +40');

    await page.selectOption('#pick-ender', 'back-throw');
    expect((await text('#reach') || '').startsWith('Reach:'), 'back throw should show its reach note');
    expect(errors.length === 0, `script errors ${errors.join(' | ')}`);
    await ctx.close();
  }
  await browser.close();
  if (failures.length) { console.error('FAIL\n' + failures.join('\n')); process.exit(1); }
  console.log('OK: picker, number entry, no-answer state, knockdown range and reach note all render at 390x844 in light and dark');
})();
