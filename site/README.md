# Studio documentation site

The public docs at <https://studio.vukem.dev>. Astro 7 (static build), React islands, Tailwind CSS v4, Base UI, and MDX. The shell is the vukem.dev documentation site, with Studio content.

`/` redirects to `/docs/introduction`.

## Scripts

```bash
npm ci
npm run dev
npm run lint
npm run check:mdx
npm run build
npm start
```

`npm run build` writes `dist/`. `npm start` serves it on `PORT` (default 3000): `/` and `/docs` answer 307 to `/docs/introduction`, and every page answers with or without a trailing slash. The root `Dockerfile` runs the same server with Bun 1.4.4.

## Last updated

Each doc page shows the last git commit that touched its MDX file. `content/last-updated.json` is the fallback for a build that does not have full history. Refresh it from the repository root of a full clone:

```bash
npm run last-updated
```

Run that inside `site/` after the MDX commits exist.

## Changelog

The site renders `../CHANGELOG.md` at build time.
