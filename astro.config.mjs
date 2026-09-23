import { defineConfig } from 'astro/config';
import { loadProviderConfig } from './scripts/provider-config.mjs';

const provider = loadProviderConfig();

export default defineConfig({
  site: 'https://graafg.github.io',
  base: provider.base,
  output: 'static',
  trailingSlash: 'always',
  // Preserve Astro 6's spacing between inline elements.
  compressHTML: true,
  build: {
    assets: '_assets',
  },
  vite: {
    build: {
      // Keep the previous CSS output and media-query browser compatibility.
      cssMinify: 'esbuild',
    },
  },
});
