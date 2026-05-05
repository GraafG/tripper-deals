/**
 * Generates public/og-default.png — the branded Open Graph image used
 * across all pages when no deal-specific image is available.
 * Run once: node scripts/generate-og.mjs
 */
import sharp from 'sharp';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve } from 'path';

const W = 1200, H = 630;

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#dc2626"/>
      <stop offset="100%" stop-color="#b91c1c"/>
    </linearGradient>
    <linearGradient id="circ" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="rgba(255,255,255,0.08)"/>
      <stop offset="100%" stop-color="rgba(255,255,255,0.01)"/>
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="${W}" height="${H}" fill="url(#bg)"/>

  <!-- Decorative circles -->
  <circle cx="980" cy="80"  r="340" fill="url(#circ)"/>
  <circle cx="150" cy="540" r="220" fill="url(#circ)"/>

  <!-- Plane shape (Material Design "flight" icon, scaled 4x) -->
  <g transform="translate(72, 82) scale(4)">
    <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" fill="white"/>
  </g>

  <!-- Brand name -->
  <text x="190" y="160" font-size="76" font-weight="800"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif" fill="white"
        letter-spacing="-1">Tripper Deals</text>

  <!-- Tagline -->
  <text x="80" y="235" font-size="36"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif"
        fill="rgba(255,255,255,0.78)">
    Vakantieaanbiedingen in één overzicht
  </text>

  <!-- Divider -->
  <line x1="80" y1="270" x2="520" y2="270" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>

  <!-- Feature bullets -->
  <text x="80" y="330" font-size="32" fill="rgba(255,255,255,0.70)"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif">✓  Vergelijk prijzen en trends</text>
  <text x="80" y="385" font-size="32" fill="rgba(255,255,255,0.70)"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif">✓  Prijsgeschiedenis per deal</text>
  <text x="80" y="440" font-size="32" fill="rgba(255,255,255,0.70)"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif">✓  Mis nooit een aanbieding</text>

  <!-- Price badge -->
  <rect x="78" y="490" width="320" height="66" rx="10" fill="rgba(0,0,0,0.25)"/>
  <text x="100" y="535" font-size="36" font-weight="700"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif"
        fill="#fbbf24">Gratis &amp; dagelijks bijgewerkt</text>

  <!-- URL bottom right -->
  <text x="${W - 60}" y="${H - 36}" font-size="26"
        font-family="system-ui,-apple-system,Segoe UI,sans-serif"
        fill="rgba(255,255,255,0.40)" text-anchor="end">
    graafg.github.io/tripper-deals
  </text>
</svg>`;

const outPath = resolve('public', 'og-default.png');
mkdirSync('public', { recursive: true });

await sharp(Buffer.from(svg))
  .png({ compressionLevel: 8 })
  .toFile(outPath);

console.log(`✅ Generated ${outPath}`);
