# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **security:** Vendor the Cloudflare security-audit skill and run it on pull requests (guidance mode)
- **app:** Video jobs at `/videos`: validated brief, compiled prompt, Claude and OpenAI adapters plus a fake adapter, validated scene plan, FFmpeg text-card renderer with ffprobe QA, queue worker with progress, job list and detail, download, retry, and per-user isolation
- **app:** Limits: output-token and cost cap per job, rolling 24-hour job quota behind a per-user lock, at most three attempts per job
- **app:** `video-text-cards` style skill that the FFmpeg renderer renders as written
- **deploy:** `Dockerfile.app` ships ffmpeg, a font, the skill catalog and `QUEUE_CONNECTION=database`; `railway.app.toml` runs `migrate` before traffic and checks `/up`
- **docs:** Quickstart, configuration, jobs, app deployment and security pages
- **test:** Go flow tests and parallel-request tests for quota, claim and retry; env-flagged real FFmpeg and real Claude tests

### Changed

- Bump vukem to v0.38.0
- **site:** The documentation site is built with Astro on the vukem.dev site shell instead of Next.js. Build `npm run build` (writes `dist/`), start `npm start`; `/` and `/docs` answer 307 to `/docs/introduction`
- The posts example resource is gone; the dashboard links to videos

### Removed

- Next.js dependencies and configuration from `site/`

### Fixed

- CI markdown lint and the Betterleaks scan: bare URLs are wrapped, the phase 5 and 6 audit headings match the outline, and auth fixture passwords are allowlisted

### Changed

- GitHub repository is [AlexGalhardo/vukem-studio](https://github.com/AlexGalhardo/vukem-studio). The public site stays `studio.vukem.dev`

### Added

- Vukem application shell: Inertia React, sidebar dashboard at `/`, Google-only login page, and session redirect tests
- App CI jobs: gofmt, `go vet`, `go test -race`, govulncheck, Betterleaks, and a `Dockerfile.app` image build
- Dependabot for Go modules, GitHub Actions, Docker, and the npm lockfiles
- Documentation site in `site/`, using the vukem.dev docs shell, with the Studio pipeline, tools, skills, and deploy guides
- Research notes, translated tool catalog, translated studio kit, and brainstorm record under `docs/`
- Video and engineering skill kits unpacked into `.agents/skills/`
- Repository hygiene: MIT license, contributing guide, security policy, code of conduct, editorconfig, markdownlint, Biome 2, git-cliff, commit-msg hook, Scorecard workflow, and a `v*` GitHub release workflow
- Docker image and Railway config for the documentation site
- `.railwayignore` so CLI uploads skip skill media, and a generated Railway config draft in `.railway/railway.ts` (not applied)
- Bun 1.4.4 typecheck script (`bun run check`)
