// Capture Capcom's official pages in a real browser (the site refuses plain HTTP clients)
// and write exact rendered content to a scratch directory. tools/fetch_capcom.py registers
// the results as snapshots.
// Usage: node tools/capcom_capture.js <out_dir> frame <character-slug>
//        node tools/capcom_capture.js <out_dir> patches
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36';

async function open(ctx, url) {
  const page = await ctx.newPage();
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForTimeout(3500);
  return { page, status: resp ? resp.status() : 0 };
}

function tableRows() {
  // Every table row as an array of cell texts, whitespace collapsed. No interpretation here.
  return Array.from(document.querySelectorAll('table tr')).map(tr =>
    Array.from(tr.querySelectorAll('th,td')).map(c => c.innerText.replace(/\s+/g, ' ').trim()));
}

(async () => {
  const [outDir, mode, arg] = process.argv.slice(2);
  fs.mkdirSync(outDir, { recursive: true });
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch({ proxy: proxy ? { server: proxy } : undefined });
  const ctx = await browser.newContext({ locale: 'en-US', userAgent: UA, viewport: { width: 1600, height: 1200 } });
  const result = { mode, pages: [] };

  if (mode === 'frame') {
    const url = `https://www.streetfighter.com/6/en-us/character/${arg}/frame`;
    const { page, status } = await open(ctx, url);
    const rows = status === 200 ? await page.evaluate(tableRows) : [];
    const title = await page.title();
    fs.writeFileSync(path.join(outDir, `frame-${arg}.rows.json`), JSON.stringify(rows, null, 0));
    fs.writeFileSync(path.join(outDir, `frame-${arg}.html`), await page.content());
    result.pages.push({ url, status, title, rows: rows.length });
  } else if (mode === 'patches') {
    const base = 'https://www.streetfighter.com/6/buckler/en/battle_change';
    const { page, status } = await open(ctx, base);
    const versions = await page.evaluate(() =>
      Array.from(document.querySelectorAll('select option')).map(o => ({ value: o.value, text: o.textContent.trim() })));
    fs.writeFileSync(path.join(outDir, 'versions.json'), JSON.stringify(versions, null, 0));
    result.pages.push({ url: base, status, title: await page.title(), versions: versions.length });
    for (const [lang, id, sub] of [['en', '20261013', ''], ['ja-jp', '20261013', ''], ['en', '20261013', '/ryu'], ['en', '20260803', '/ryu']]) {
      const url = `https://www.streetfighter.com/6/buckler/${lang}/battle_change/${id}${sub}`;
      const p = await open(ctx, url);
      const text = await p.page.evaluate(() => document.body.innerText);
      const name = `battle_change-${id}-${lang}${sub.replace('/', '-')}.txt`;
      fs.writeFileSync(path.join(outDir, name), text);
      result.pages.push({ url, status: p.status, title: await p.page.title(), chars: text.length, file: name });
      await p.page.close();
    }
  }
  await browser.close();
  console.log(JSON.stringify(result));
})().catch(e => { console.error(String(e)); process.exit(1); });
