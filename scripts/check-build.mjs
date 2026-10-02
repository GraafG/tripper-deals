import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { join, relative } from 'node:path';
import { Script } from 'node:vm';
import sharp from 'sharp';
import { ELEMENT_NODE, TEXT_NODE, parse, walkSync } from 'ultrahtml';
import { loadProviderConfig } from './provider-config.mjs';

const provider = loadProviderConfig(process.argv[2]);
const read = path => readFileSync(path, 'utf8');
const json = path => JSON.parse(read(path));
const home = read('dist/index.html');
const privacy = read('dist/privacy/index.html');
assert.ok(home.includes(`name="site-base" content="${provider.base}/"`), 'Provider base must survive compilation');
assert.ok(home.includes(`href="${provider.siteUrl}/"`), 'Canonical URL must match the provider');
assert.match(privacy, /<strong>Niets\.<\/strong> Tripper Deals/, 'Inline HTML spacing must be preserved');
assert.match(home, /window\.showView\s*=\s*showView/);
assert.match(home, /window\.toggleSparkline\s*=\s*toggleSparkline/);
walkSync(parse(home), node => {
  if (node.type !== ELEMENT_NODE || node.name.toLowerCase() !== 'script') return;
  const attributes = Object.keys(node.attributes).map(name => name.toLowerCase());
  if (attributes.includes('type') || attributes.includes('src')) return;
  new Script(node.children.filter(child => child.type === TEXT_NODE).map(child => child.value).join(''));
});

const cssFiles = readdirSync('dist/_assets').filter(path => path.endsWith('.css'));
assert.ok(cssFiles.length, 'Build must emit styles');
const css = cssFiles.map(path => read(join('dist/_assets', path))).join('\n');
assert.match(css, /@media\s*\(min-width:\s*640px\)/);
assert.doesNotMatch(css, /@media\s*\(width\s*[<>]=/, 'Do not narrow media-query browser support');

const cache = provider.dealCachePath ? json(provider.dealCachePath) : {};
const fields = ['lat', 'lng', 'address', 'locations', 'image_url', 'review_count'];
const files = readdirSync(provider.dataDir, { recursive: true, withFileTypes: true }).filter(entry => entry.isFile());
for (const entry of files) {
  const source = join(entry.parentPath, entry.name);
  const dataPath = relative(provider.dataDir, source);
  const destination = join('dist/data', dataPath);
  if (/^\d{4}[/\\]\d{2}[/\\]\d{2}\.json$/.test(dataPath)) {
    const expected = json(source).map(deal => {
      const enriched = { ...deal };
      for (const field of fields) {
        if (cache[deal.url]?.[field] != null && enriched[field] == null) {
          enriched[field] = cache[deal.url][field];
        }
      }
      return enriched;
    });
    assert.deepEqual(json(destination), expected, `Snapshot enrichment changed: ${dataPath}`);
  } else {
    assert.deepEqual(readFileSync(destination), readFileSync(source), `Data changed: ${dataPath}`);
  }
}
assert.equal(
  readdirSync('dist/data', { recursive: true, withFileTypes: true }).filter(entry => entry.isFile()).length,
  files.length,
  'No stale or missing provider data files',
);

const feed = read('dist/feed.xml');
assert.match(feed, /<rss\b/);
assert.ok(feed.includes(`${provider.siteUrl}/`), 'Feed URLs must use the provider URL');
assert.ok(read('dist/sitemap.xml').includes(`${provider.siteUrl}/`), 'Sitemap URLs must use the provider URL');
const images = readdirSync('dist/og').filter(path => path.endsWith('.png'));
assert.ok(images.length, 'Active deals must have generated OG images');
for (const file of ['dist/og-default.png', ...images.map(path => join('dist/og', path))]) {
  const metadata = await sharp(file).metadata();
  assert.equal(metadata.format, 'png', file);
  assert.equal(metadata.width, 1200, file);
  assert.equal(metadata.height, 630, file);
}
console.log(`${provider.id}: HTML/CSS/feed, ${files.length} data files and ${images.length + 1} OG images passed.`);
