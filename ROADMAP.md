# Roadmap

Studio is an open source short-form video studio. A person fills a brief. The app compiles a prompt, a worker renders an MP4, and a check decides whether that file is ready.

Legend: `[x]` done, `[/]` partial, `[ ]` not started. A phase is done only when every audit box under it is `[x]`.

## Phase 0 — Repository foundation

### 0.1 Source of truth

- [x] GitHub repository `AlexGalhardo/vukem-studio` exists
- [x] `docs/recommend-tools.md` and `docs/video-studio-kit.md` read and translated to English
- [x] Skill archives unpacked into `.agents/skills/`
- [x] `docs/web-research.md` records the pipeline evidence
- [x] `docs/brainstorming.md` records open questions and the guesses the scaffold used
- [x] `vukem-feedback.md` exists locally and is gitignored

### 0.2 Project hygiene

- [x] `LICENSE` (MIT), `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- [x] Semantic Versioning stated in the README and `CHANGELOG.md` (Keep a Changelog)
- [x] Conventional Commits: `.githooks/commit-msg` and the PR title workflow
- [x] `cliff.toml` for changelog generation
- [x] `.editorconfig`, `.markdownlint-cli2.jsonc`, `biome.json` (Biome 2 schema)
- [x] Bun `1.4.4` named as the frontend typecheck runtime (`bun run check`)
- [x] OpenSSF Scorecard workflow with `publish_results`
- [x] Docker image for the docs site, non-root, pinned Bun tag
- [x] `.agents/rules/` for repository rules
- [/] Skill kits remain in Portuguese. Translate a kit when a job actually calls it.

#### Audit — phase 0

- [x] A fresh clone has `ROADMAP.md`, `site/`, and `.github/workflows/`
- [x] `git check-ignore -v vukem-feedback.md` points at `.gitignore`
- [x] `bun run check` exits 0 on the docs site (`tsc --noEmit`)
- [x] `npm run check:mdx` and `npm run build` inside `site/` exit 0
- [ ] Scorecard workflow has run on `main` at least once

## Phase 1 — Documentation site is public

The visitor of `studio.vukem.dev` lands on the technical introduction.

### 1.1 Site

- [x] `site/` uses the vukem.dev docs shell (Astro 7, MDX, sidebar, search, changelog page)
- [x] `/` redirects to `/docs/introduction`
- [x] Pages exist for the pipeline, tools, skills, and deploy
- [x] `content/last-updated.json` is filled from git and `npm run check:last-updated` passes

### 1.2 Host

- [x] `Dockerfile` builds the site as a standalone server
- [x] Railway project `studio`, service deployed from the Dockerfile. Live host: `https://studio-production-b48f.up.railway.app` (`/` is 307 to `/docs/introduction`, introduction is 200)
- [ ] `studio.vukem.dev` CNAME `studio` → `oqw3fjl4.up.railway.app` (record not in DNS yet)
- [ ] `https://studio.vukem.dev/docs/introduction` returns 200
- [ ] `https://studio.vukem.dev/` redirects to the introduction

#### Audit — phase 1

- [ ] Homepage redirect and the introduction render without a console error
- [x] One inner page (`/docs/pipeline/overview`) renders the sidebar and the article
- [x] Changelog page renders `CHANGELOG.md`
- [x] `trading.vukem.dev` is not attached to this service

## Phase 2 — Application shell

A Vukem app with Inertia and React. This phase produces no video.

### 2.1 App

- [x] `vukem new` (or the equivalent layout from the current vukem docs) creates the app module
- [x] Inertia React adapter and a sidebar layout
- [x] Route `/` renders the dashboard for a signed-in user
- [x] Missing session on any private route redirects to `/login`
- [x] `/login` shows one control: "Continue with Google"
- [x] Sign-out returns to `/login`
- [x] English UI strings

### 2.2 Session

- [x] Google OAuth client id and secret come from the environment, validated at boot
- [x] Session cookie is `HttpOnly`, `Secure`, and `SameSite` as the vukem security docs require
- [x] A test covers the redirect when the session is missing
- [x] A test covers a signed-in request reaching `/`

#### Audit — phase 2

- [x] `go test` for the auth redirect passes
- [x] Browser: signed out, `/` ends on `/login`
- [x] Browser: Google button is the only sign-in control
- [x] Browser: after a test session, `/` shows the sidebar
- [ ] Docs site on `studio.vukem.dev` still serves the introduction

## Phase 3 — Brief to a stored prompt

No pixels yet. The dashboard writes a job the worker can read.

### 3.1 Brief form

- [x] Fields from [the brief page](site/content/docs/pipeline/brief.mdx): goal, audience, subject, duration, ratio, style skill, language, facts, links, call to action
- [x] Server-side validation. The browser is not the gate
- [x] Style skill must be an id that exists under `.agents/skills/`
- [x] Empty required field returns a field error, not a 500

### 3.2 Compiler

- [x] Compiler builds one prompt from the brief plus the chosen skill
- [x] Must-keep facts are copied in as constraints
- [x] Frame size and duration are in the prompt
- [x] The job row stores the prompt text, the skill id, and the model id
- [x] The operator can read the prompt in the dashboard

#### Audit — phase 3

- [x] Test: missing goal is rejected
- [x] Test: unknown style id is rejected
- [x] Test: a fact string in the brief is present in the stored prompt
- [ ] Browser: submit a valid brief and see the stored prompt

## Phase 4 — First MP4

The definition of done for this phase is one silent 9:16 file from a brief, checked by ffprobe.

### 4.1 Plan

- [x] Model adapter (one provider) returns a scene plan as structured data
- [x] Invalid model output is a failed job with the raw response stored
- [x] Duration on the plan fits the brief

### 4.2 Render

- [/] Worker renders the silent style through HyperFrames or Remotion (the text-card style renders with FFmpeg alone; Remotion and HyperFrames styles are not wired)
- [x] FFmpeg encodes H.264, `yuv420p`, `+faststart`, no audio stream
- [x] Job status moves `queued -> rendering -> ready` or `failed`
- [x] Retry does not leave a second public file for the same job
- [x] Sidecar stores renderer version, FFmpeg version, skill id, prompt

### 4.3 Check

- [/] QA rules on [the QA page](site/content/docs/pipeline/qa.mdx) for a silent file
- [x] A truncated file stays `failed`
- [x] Dashboard offers download only when status is `ready`

#### Audit — phase 4

- [x] Fixture brief renders in CI or a documented local command (no network key required for the silent path)
- [x] `ffprobe` on the fixture output matches ratio, pixel format, and faststart
- [x] Failed fixture (killed encoder) stays `failed` and is not downloadable
- [ ] Browser: brief, wait, download, file plays

## Phase 5 — Spoken cut

- [ ] Voice input: upload, or a local TTS adapter
- [ ] Whisper word times
- [ ] Burned-in captions match the cue file
- [ ] Loudness gate at -14 LUFS ±2 LU and true peak ≤ -1.5 dBTP
- [ ] Music bed only with a license record, ducked under the voice
- [ ] Fact list: each must-keep fact still appears in the stored script

### Audit — phase 5

- [ ] Fixture with a 5-second voice passes loudness and caption checks
- [ ] Fixture that drops a must-keep fact fails the job
- [ ] A bed without a license is absent from the file

## Phase 6 — Library and publish pack

- [x] Job list with status, duration, and style
- [ ] Re-run keeps the previous ready file until the new one passes
- [ ] Publish pack: title, description, hashtags, and `.srt`, validated against the limits in the publication skill
- [ ] No automatic post to a social network in this phase

### Audit — phase 6

- [x] Two jobs from one user do not leak across a second test user
- [ ] Publish pack rejects a title over the platform limit named in the skill
- [ ] Browser: list, open, download, see the pack

## Explicitly later

- [ ] Extra aspect ratios exported from the same plan
- [ ] Pixel-video model adapter
- [ ] Avatar or face
- [ ] Team roles and billing
- [ ] Direct upload to YouTube, Instagram, or TikTok
- [ ] Translation of every skill kit
- [ ] GoReleaser archives, SBOM, and cosign on the GitHub release, once the app ships a binary

## Feedback to the Vukem framework

Write framework bugs and gaps in `vukem-feedback.md` (gitignored) as they show up during phase 2. Do not "fix" them inside Studio by forking the framework.
