import assert from 'node:assert/strict';
import { realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import sharp from 'sharp';
import sharpService from 'astro/assets/services/sharp';

const require = createRequire(import.meta.url);
const astroRequire = createRequire(import.meta.resolve('astro'));
assert.equal(
  realpathSync(astroRequire.resolve('sharp')),
  realpathSync(require.resolve('sharp')),
  'Astro must use the same patched Sharp as the OG image generator',
);

function atLeast(actual, minimum) {
  const actualParts = actual.split('.').map(Number);
  const minimumParts = minimum.split('.').map(Number);
  assert.equal(actualParts.length, 3, `Unexpected version: ${actual}`);
  assert.ok(actualParts.every(Number.isInteger), `Unexpected version: ${actual}`);
  for (let index = 0; index < 3; index++) {
    if (actualParts[index] !== minimumParts[index]) {
      return actualParts[index] > minimumParts[index];
    }
  }
  return true;
}

assert.ok(atLeast(sharp.versions.sharp, '0.35.4'), 'Sharp must include the AVIF fix');
assert.ok(atLeast(sharp.versions.heif, '1.23.2'), 'The loaded libheif must be patched');

const svg = Buffer.from('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="32"><rect width="64" height="32" fill="#dc2626"/></svg>');
const png = await sharp(svg).png().toBuffer();
const avif = await sharp(png).avif({ lossless: true }).toBuffer();
const config = { service: { config: {} } };

for (const format of ['png', 'webp', 'avif']) {
  const result = await sharpService.transform(
    avif,
    { src: '/fixture.avif', width: 32, height: 16, format },
    config,
  );
  const metadata = await sharp(result.data).metadata();
  assert.equal(metadata.width, 32, `AVIF to ${format} must resize, not silently pass through`);
  assert.equal(metadata.height, 16);
  assert.equal(metadata.format, format === 'avif' ? 'heif' : format);
  if (format === 'avif') assert.equal(metadata.compression, 'av1');
  await sharp(result.data).raw().toBuffer();
}

const passthrough = await sharpService.transform(svg, { src: '/fixture.svg', format: 'svg' }, config);
assert.deepEqual(passthrough.data, svg);
await assert.rejects(
  sharpService.transform(svg, { src: '/fixture.svg', format: 'png' }, config),
  /SVG image processing is disabled/,
);
await assert.rejects(
  sharpService.transform(Buffer.from('invalid image'), { src: '/invalid.avif', format: 'png' }, config),
  /metadata/i,
);

console.log(`Image checks passed: Sharp ${sharp.versions.sharp}, libheif ${sharp.versions.heif}; SVG/PNG and Astro AVIF transforms.`);
