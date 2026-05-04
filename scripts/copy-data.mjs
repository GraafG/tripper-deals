import { cpSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');
const src = join(root, 'data');
const dst = join(root, 'dist', 'data');

cpSync(src, dst, { recursive: true });
console.log('✅ data/ copied to dist/data/');
