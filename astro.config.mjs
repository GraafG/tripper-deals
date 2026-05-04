import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://graafg.github.io',
  base: '/tripper-deals',
  output: 'static',
  trailingSlash: 'always',
  build: {
    assets: '_assets',
  },
});
