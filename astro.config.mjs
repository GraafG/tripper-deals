import { defineConfig } from 'astro/config';
import { loadProviderConfig } from './scripts/provider-config.mjs';

const provider = loadProviderConfig();

export default defineConfig({
  site: 'https://graafg.github.io',
  base: provider.base,
  output: 'static',
  // Preserve HTML-aware inline spacing instead of Astro 7's JSX whitespace rules.
  compressHTML: true,
  trailingSlash: 'always',
  build: {
    assets: '_assets',
  },
});
