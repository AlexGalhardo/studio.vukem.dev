# Studio documentation site

The public docs at <https://studio.vukem.dev>. Next.js 16 (App Router, static generation), Tailwind CSS v4, Base UI, and MDX. The shell is the vukem.dev documentation site, with Studio content.

`/` redirects to `/docs/introduction`.

## Scripts

```bash
npm ci
npm run dev
npm run check
npm run lint
npm run check:mdx
npm run build
```

`check` runs `tsc --noEmit`. From the repository root, `bun run check` runs the same script with Bun 1.4.4.

## Last updated

Each doc page shows the last git commit that touched its MDX file. `content/last-updated.json` is the fallback for a build that does not have full history. Refresh it from the repository root of a full clone:

```bash
npm run last-updated
```

Run that inside `site/` after the MDX commits exist.

## Changelog

The site renders `../CHANGELOG.md` at build time.
