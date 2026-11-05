# Contributing

Thank you for working on Studio. The product goal is in [ROADMAP.md](ROADMAP.md). The public docs live in `site/`.

## Setup

- Git
- Node.js 24, used by the docs site the same way the vukem.dev site is built
- [Bun 1.4.4](https://bun.sh) for `bun run check`
- Docker, only if you are building the image

```bash
git clone https://github.com/AlexGalhardo/vukem-studio.git
cd vukem-studio
git config core.hooksPath .githooks
bun install
cd site
npm ci
npm run dev
```

The site listens on the port Next prints. `/` redirects to `/docs/introduction`.

## Checks

Run the ones your change can affect.

| Change | Command |
| --- | --- |
| Go app | `go test -count=1 ./tests/` |
| App TypeScript | `bun run typecheck` from the repository root |
| TypeScript in `site/` | `bun run check` from the repository root |
| MDX docs | `npm run check:mdx` inside `site/` |
| ESLint in `site/` | `npm run lint` inside `site/` |
| Markdown outside `.agents/` | `npx markdownlint-cli2` |
| Docs production build | `npm run build` inside `site/` |

`.agents/skills/` is ignored by markdownlint until those kits are translated. Do not "fix" them by silencing a rule in a kit you were not asked to edit.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) in English.

```text
feat(docs): add the render page
fix(site): keep the changelog path at the repo root
```

The subject is lowercase and has no final period. Types: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore`, `style`, `revert`.

One logical change per commit. Update `CHANGELOG.md` under `[Unreleased]` when the change is user-visible or changes a command.

## Pull requests

Branch from `main`. Open the pull request against `main`. The title uses the same conventional header as the commit. `main` is a protected branch: green checks, linear history.

## Skills

A visual skill under `.agents/skills/` is data for the future prompt compiler. Add a skill by unpacking it into its own directory and listing the id on the catalog page. Do not commit `zip/`.
