# Studio rules

- Write code, docs, commits, and UI in English.
- The public site is the documentation at `studio.vukem.dev`. Do not attach `trading.vukem.dev`.
- The product app, when it exists, is a Vukem app: Inertia, React, sidebar dashboard, Google-only login, redirect to `/login` when signed out.
- Do not put a video API key, OAuth secret, or session secret in the repository.
- The prompt compiler reads a skill from `.agents/skills/`. It does not invent a second visual system.
- FFmpeg is invoked with an argument list, never a shell string built from the brief.
- A render is not ready until the QA checks in `site/content/docs/pipeline/qa.mdx` pass.
- External media ships only with a license record.
- Framework bugs go in `vukem-feedback.md` at the workspace root (shared by all projects, ids `ST-<n>`). Do not fork Vukem to paper over them.
- Quotas, job claims and retries are conditional SQL updates or transactions behind a lock, never read-then-write. Window queries compare integers (`created_unix`), not timestamp text.
- Tests use the fake adapter (`STUDIO_PROVIDER=fake`). Real FFmpeg and real model tests stay behind `STUDIO_TEST_FFMPEG=1` and `STUDIO_TEST_REAL_MODEL=1`.
- The docs site in `site/` is Astro, same shell as `vukem/site`. Run `npm run check:mdx`, `npm run lint` and `npm run build` there.
- Skill kits are still Portuguese. Translate the kit you are wiring, not the whole tree, unless the task says otherwise.
- Do not commit `zip/`.
- Apply the vendored `security-audit` skill (`.agents/skills/security-audit`, Cloudflare) during development, in guidance mode unless the task is an explicit full audit. CI runs it in `.github/workflows/security-audit.yml`.
