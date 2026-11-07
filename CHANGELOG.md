# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **security:** Vendor the Cloudflare security-audit skill and run it on pull requests (guidance mode)

### Changed

- Bump vukem to v0.38.0

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
