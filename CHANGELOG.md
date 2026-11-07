# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **app:** Videos up to 300 seconds (was 45); plan shots, output tokens and the queue timeout scale with the duration
- **security:** Vendor the Cloudflare security-audit skill and run it on pull requests (guidance mode)
- **app:** Claude (`claude-sonnet-5-5`, `claude-opus-5-5`) and OpenAI planners behind the planner interface, selected by `STUDIO_MODEL` or `ANTHROPIC_API_KEY`; a missing key fails the job with the variable name
- **app:** Rolling 24-hour job quota behind a per-user lock, integer-epoch window, worst-case cost cap per job, output-token cap, and at most five renders per job
- **deploy:** `railway.app.toml` runs `migrate` before traffic and checks `/up`; `Dockerfile.app` ships the skill files and `QUEUE_CONNECTION=database`
- **docs:** Quickstart, configuration, jobs, app deployment and security pages
- **test:** Parallel-request tests for quota, claim and requeue; an env-flagged real Claude test; a hung-encoder deadline test
- Video jobs: a brief form, server-side validation, a prompt compiler, a local scene planner, an FFmpeg renderer, QA, captions, loudness, a music bed that requires a license, a job library, and a publish pack that is not posted
- Optional HyperFrames and Remotion renderer commands selected with `STUDIO_RENDERER`
- English visual law `SKILL.en.md` for `traco-simples`, the style the default brief attaches
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

### Changed

- **docs:** Agent rules cover the shared feedback file (`ST-` ids), the pinned Astro site and `last-updated`, the canonical jobs pipeline, tests, and Railway service, volume and domain rules
- Bump vukem to v0.38.0
- **site:** The documentation site is built with Astro on the vukem.dev site shell instead of Next.js. Build `npm run build` (writes `dist/`), start `npm start`; `/` and `/docs` answer 307 to `/docs/introduction`
- Claim and retry of a job are conditional SQL updates, so duplicate deliveries and parallel retries cannot render or bill twice
- Every ffmpeg, ffprobe and renderer process has a five-minute deadline
- GitHub repository is [AlexGalhardo/vukem-studio](https://github.com/AlexGalhardo/vukem-studio). The public site stays `studio.vukem.dev`

### Removed

- The starter's posts CRUD (it was public, unauthenticated), its seeder, factory and pages
- Next.js dependencies and configuration from `site/`, and the pt-br redirect component (an open redirect)

### Fixed

- **security:** A voice upload whose WAV header understates its length no longer crashes the process; the declared data size is honored and the decoded length is checked before resampling (ST-SEC-001)
- Captions with control characters, braces or backslashes are rejected in a plan instead of reaching libass
- The docs server answers 400 on malformed percent-encoding instead of failing
- CI markdown lint and the Betterleaks scan: bare URLs are wrapped, the phase 5 and 6 audit headings match the outline, and auth fixture passwords are allowlisted
