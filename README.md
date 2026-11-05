<div align="center">

<h1><strong><a href="https://studio.vukem.dev" style="text-decoration: none" target="_blank">studio.vukem.dev</a></strong></h1>

[![CI](https://github.com/AlexGalhardo/studio.vukem.dev/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexGalhardo/studio.vukem.dev/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Bun 1.4.4](https://img.shields.io/badge/bun-1.4.4-000000?logo=bun&logoColor=white)](package.json)
<a href="https://github.com/AlexGalhardo/studio.vukem.dev/releases"><img src="https://img.shields.io/github/v/release/AlexGalhardo/studio.vukem.dev?include_prereleases&label=version" alt="Version"></a>

<a href="https://scorecard.dev/viewer/?uri=github.com/AlexGalhardo/studio.vukem.dev"><img src="https://api.scorecard.dev/projects/github.com/AlexGalhardo/studio.vukem.dev/badge" alt="OpenSSF Scorecard"></a>

<h3><strong>Open source studio for short-form video</strong></h3>

</div>

## Introduction

Studio turns a video brief into a rendered MP4 for Shorts, Reels, and other short social cuts. The dashboard collects the goal, the audience, and the visual style. A compiler writes the prompt. A worker renders the file with open source tools.

The application will be built with the [Vukem](https://vukem.dev) Go framework. This repository currently ships the documentation site, the research, and the skill kits.

Opening [studio.vukem.dev](https://studio.vukem.dev) lands on the technical documentation.

## Summary

- [Introduction](#introduction)
- [Stability](#stability)
- [Contributing](#contributing)
- [Code of conduct](#code-of-conduct)
- [Security vulnerabilities](#security-vulnerabilities)
- [License](#license)

## Stability

Studio follows [Semantic Versioning](https://semver.org) and tags releases as `vX.Y.Z` on `main`. The first release is `v0.1.0`.

Changes are listed in [CHANGELOG.md](CHANGELOG.md), which follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

The work still ahead is tracked in [ROADMAP.md](ROADMAP.md). A box marked `[/]` is only partly done.

## Contributing

Thank you for considering a contribution to Studio.

- Read [ROADMAP.md](ROADMAP.md) and the docs under `site/content` before changing behavior.
- Keep the repository in English.
- Run the check that covers your change. For the docs site that is `bun run check` and `npm run check:mdx` inside `site/`.
- Update `CHANGELOG.md` under `[Unreleased]` when behavior, commands, or conventions change.

The full guide is in [CONTRIBUTING.md](CONTRIBUTING.md).

### Pull requests

1. Create a branch from `main`.
2. Make one logical change per commit.
3. Open a pull request against `main`.

`main` accepts changes only through a pull request with green required checks and linear history.

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) in English: `type(scope): description`.

- Types: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore`, `style`, `revert`.
- The subject starts with a lowercase letter and does not end with a period.

Enable the local hook once:

```bash
git config core.hooksPath .githooks
```

The pull request title workflow checks the same rule in CI.

## Code of conduct

To keep the community welcoming to everyone, please review and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security vulnerabilities

If you discover a security vulnerability, please follow the [security policy](SECURITY.md) instead of opening a public issue.

## License

Studio is open source software released under the [MIT license](LICENSE).
