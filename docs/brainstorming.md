# Brainstorming

Date: 2026-11-04.

This file is the interview record. It states the working hypothesis, the questions that are still open, and the technical proposals already used so the repository could move. An open question is not a silent decision.

## Hypothesis

You want a Vukem dashboard that compiles a short-form video brief into a prompt, renders an MP4 with open source tools, and a documentation site on `studio.vukem.dev` that uses the same docs shell as vukem.dev.

Confidence: about 80%. Hostname is `studio.vukem.dev`. Still open: whether the first render must include a voice, and whether Remotion is acceptable under its company license.

## What was taken as given

- English in the repository: docs, UI, commits, comments.
- The docs site is Astro (static build) and matches the vukem.dev docs shell. `/` on that site redirects to the introduction.
- The product application is a separate Vukem app: Inertia, React, shadcn-style sidebar. `/` is the dashboard. A signed-out session redirects to `/login` with a single Google button.
- The render path is FFmpeg plus Remotion, with a language model writing the plan. HyperFrames is the permissive alternative recorded in the research.
- Skills from `zip/` live in `.agents/skills/`.
- Releases follow semantic versions and Conventional Commits, and publish GitHub releases. Binary archives wait until a binary exists.
- `vukem-feedback.md` exists and is gitignored.

## Questions

Each question has a guess. The guess is what the scaffold assumed when the work could not wait. Correct any line that is wrong.

### 1. Hostname

Q: The brief says the site is `studio.vukem.dev`, and task (a) says the web process should answer on `trading.vukem.dev`. Which hostname is this product?

Decision, already deployed: `studio.vukem.dev`. `trading` is a separate Railway project on this account. This service lists `studio-production-b48f.up.railway.app` and `studio.vukem.dev` only. `trading.vukem.dev` is not attached.

DNS for `studio.vukem.dev` is still empty. The CNAME is `studio` to `oqw3fjl4.up.railway.app`.

### 2. First video that counts as done

Q: If you did not have to justify the architecture, what is the first MP4 you want out of the dashboard?

Guess: a silent 9:16 motion piece in one style skill, from a form, with no voice and no stock footage. Voice, captions, and b-roll come after that file exists.

### 3. Renderer default

Q: For a for-profit company that might grow past three people, should the default renderer be HyperFrames (Apache-2.0) or Remotion (company license past three people)?

Guess: keep both adapters, default the HTML skills to HyperFrames, and use Remotion only when the composition is React and someone has accepted the license. The job sidecar records the choice.

### 4. Who signs in

Q: Is Google login only for you, or is this a multi-user product on day one?

Guess: one operator (you) on day one. The account model still has a user id so a second person does not require a rewrite, but there is no team UI, no roles, and no billing.

### 5. Facts

Q: When the video states a number, a price, or a date, do you want the worker to block the file until a source is attached?

Guess: yes for any brief that fills "must-keep facts". A brief with that field empty may render an opinion or a fictional motion piece, and the sidecar says no facts were checked.

### 6. Skill language

Q: The unpacked skills are in Portuguese. Translate them before any product code calls them, or translate a skill only when that style is wired in?

Guess: translate the skill the first milestone actually calls, plus the art-direction kit it imports. Leave the other kits in Portuguese until a style is selected. A wholesale translation of every example project is a separate pass.

### 7. Where the docs site and the app sit

Q: One hostname with the docs at `/` and the app on a path, or the docs on `studio.vukem.dev` and the app on another name?

Guess: this hostname is the docs, because the brief says a visitor lands on the technical documentation. The dashboard is a second Railway service, for example `app.studio.vukem.dev`, after the app exists. Putting both in one process now would couple a Next.js docs build to a Go server before either is finished.

## Proposals already in the tree

- Docs content describes the pipeline, the tools, the skill catalog, and the deploy. It does not copy the Vukem framework manual.
- QA numbers (duration tolerance, loudness, pixel format, faststart) are written down so a later worker can be tested against them.
- Scorecard, conventional pull request titles, Keep a Changelog, and a `v*` release workflow match the Vukem release habit without pretending a Go binary exists.
- `zip/` is not committed. The unpacked skills are about 290 MB because of example MP4s. They are the working copy.

## Out of scope until you say otherwise

- Avatar presenters and face clones
- Direct publish to TikTok, Instagram, or YouTube
- Billing and subscriptions
- A pixel-video model (Wan, Veo, Kling, Runway, Sora) on the default path
- Translating every skill kit in one pass
