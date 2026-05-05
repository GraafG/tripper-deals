import type { APIRoute } from 'astro';
import { getAllDealDetails } from '../lib/deals';
import { SITE_URL } from '../lib/config';

const SITE = SITE_URL;

export const GET: APIRoute = () => {
  const deals = getAllDealDetails();

  const dealUrls = deals
    .filter(d => d.slug && d.isActive)
    .map(d => `  <url><loc>${SITE}/deal/${d.slug}/</loc><changefreq>daily</changefreq><priority>0.7</priority></url>`)
    .join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${SITE}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>
${dealUrls}
</urlset>`;

  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
};
