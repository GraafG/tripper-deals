import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import semver from 'semver';
import { parse, stringify } from 'devalue';
import { optimize } from 'svgo';

const minimums = {
  astro: '7.3.1',
  sharp: '0.35.4',
  esbuild: '0.28.1',
  svgo: '4.1.0',
  nanoid: '3.3.18',
  // GHSA-9rgm-9g3h-6x36's description and first_patched_version specify 5.9.2.
  devalue: '5.9.2',
  'js-yaml': '4.3.2',
};
const { packages } = JSON.parse(readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'));
for (const [name, minimum] of Object.entries(minimums)) {
  const instances = Object.entries(packages).filter(([path]) => path.endsWith(`node_modules/${name}`));
  assert.ok(instances.length, `Missing dependency: ${name}`);
  for (const [path, { version }] of instances) {
    assert.ok(semver.gte(version, minimum), `${path}: ${version} is below ${minimum}`);
    console.log(`${path}: ${version}`);
  }
}

const value = { dates: [new Date('2026-01-01')], prices: new Map([['fixture', 12.5]]) };
assert.deepEqual(parse(stringify(value)), value);
assert.throws(() => parse('[{"outOfBounds":2}]'));
const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="32"><rect width="64" height="32" fill="red"/></svg>';
assert.match(optimize(svg).data, /<svg/);
console.log('Dependency floors and synthetic devalue/SVGO checks passed.');
