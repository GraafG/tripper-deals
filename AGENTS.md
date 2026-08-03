# Agent instructions for tripper-deals

This repo is part of the shared deals tracker setup. Treat it as a provider-configured Astro site, not a one-off static page.

## Context
- Canonical template repo: `GraafG/deals-template`.
- This repo currently carries the shared Astro code and provider data for:
  - `providers/tripper` - default Tripper deployment at `https://graafg.github.io/tripper-deals/`.
  - `providers/vriendenloterij` - historical/provider data that must not be deleted.
- Provider config lives in `providers/<provider>/site.config.json`.
- Provider snapshots and history live under `providers/<provider>/data/`.
- The browser reads generated files from `public/data/` after `scripts/build-provider.mjs` copies the selected provider data.

## Commands
- Install: `npm install`
- Build Tripper: `npm run build:tripper`
- Build VriendenLoterij from this repo copy: `npm run build:vriendenloterij`
- Generic build: `node scripts/build-provider.mjs <provider>`
- Preview after build: `npm run preview`

## Rules for agents
- Never delete or rewrite price/history data unless the user explicitly asks. Preserve all historical snapshots.
- Do not run scrapers or add new data when the user asks only for UI, config, docs, or deployment fixes.
- Prefer deploy-only workflow runs when only site code/config changed.
- Keep provider-specific differences in `providers/<provider>/site.config.json`, provider data, and provider scraper/import scripts.
- Keep shared UI/build behavior in `src/` and `scripts/`, then propagate fixes back to `GraafG/deals-template`.
- GitHub Pages should stay configured for `https://graafg.github.io/tripper-deals/`.
- Use GitHub CLI (`gh`) for repo settings, PRs, workflow runs, and branch checks when possible.
- Before changing generated output, check whether it is produced by the provider build and update the source instead.

## Important implementation notes
- `src/pages/index.astro` renders inline event handlers, so any function used from `onclick` must be assigned to `window`.
- Some providers have no geo data. Gate map UI through `SITE_CONFIG.features.map`.
- Some history entries may lack a `prices` array; UI code must guard with `Array.isArray(...)`.
