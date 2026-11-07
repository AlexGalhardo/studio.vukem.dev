# Security audit, 2026-11-07

Target: `vukem-studio`, branch `feat/todo-2026-11-main` (PR 8, deployed at app.studio.vukem.dev). Method: the vendored `security-audit` skill (`.agents/skills/security-audit`), full audit mode, profile `standard`.

## Scope and coverage

In scope: the Go app (`app/`, `routes/`, `bootstrap/`, `database/`), `resources/js`, the docs site scripts (`site/scripts`, `site/components`), `.github/workflows`, `Dockerfile`, `Dockerfile.app`, `railway*.toml`. Out of scope: vendored skill content, `node_modules`, generated output.

Coverage is partial in these ways, stated so nobody reads "no finding" as "proven safe":

- One agent (the parent) ran all phases. Independent verifier agents were not used; every confirmed record was instead re-checked by a local run (findings 001 and 003) or by a direct source trace (the rest, marked in the confidence field).
- Phase 3 and 5 validators passed (`validate-findings.cjs`: 9 records; `validate-coverage-ledger.cjs`: 13 units). They refuse to run on Windows without `O_NOFOLLOW`, so they were run with a preload shim that defines that constant. No validator code was changed.
- No deployed endpoint, hosted model, container runtime or Railway setting was touched. Deployment facts are `needs_validation`.
- No prior ledger exists for this repo (`prior_status: none`).
- Ledger: `docs/security-audit-2026-11-07.coverage.json`. Records: `docs/security-audit-2026-11-07.findings.json`.

## Summary

| Id | Severity | CWE | Title | State |
| --- | --- | --- | --- | --- |
| ST-SEC-001 | High | CWE-789 | Lying WAV header crashes the whole process (fatal OOM) | fix in Phase B |
| ST-SEC-004 | Medium | CWE-770 | Retries bypass the daily quota; no global model spend cap | owner decision |
| ST-SEC-003 | Low | CWE-362 | Stale whole-row update reverts status and attempts | fix in Phase B |
| ST-SEC-005 | Low | CWE-1188 | Password auth routes still active (rule says Google-only) | owner decision |
| ST-SEC-006 | Low | CWE-61 | Root `chown -R` over an app-writable volume | fix in Phase B |
| ST-SEC-007 | not rated | CWE-532 | `MAIL_MAILER=log` image default may log reset links | needs validation |

Counts: 1 high, 1 medium, 3 low confirmed; 1 needs validation; 3 rejected.

## Findings

### ST-SEC-001, High, CWE-789 (also CWE-400)

`app/studio/audio.go:344-369`, `app/studio/run.go:263-333`, entry at `app/controllers/job_controller.go:124`.

Impact: any verified user stops the whole app process (web server and queue worker share it), including other users' renders, until Railway restarts it. Go's out-of-memory abort cannot be recovered.

Cause: `prepareVoice` trusts the duration `ffprobe` derives from the WAV header. `DecodeWAV` ignores the declared data-chunk size and reads every byte after the 44-byte header, then `resample` allocates `len(in) * 48000 / rate` floats with `rate` taken from the same header.

Reproduction (local): a WAV with sample rate 1, data size 600 and 10 MiB of trailing bytes. `ffprobe` reports `duration=300.000000`. `studio.Run` with `Duration: 300`, `Voice: upload` ends with `runtime: VirtualAlloc of 20132659200001455` and `fatal error: out of memory`. The upload passes the request check because `z.File` only sniffs RIFF/WAVE and the body cap is 10 MiB.

Fix: honor the declared data size, compare decoded duration with the brief before resampling, cap the output length.

### ST-SEC-004, Medium, CWE-770

`app/jobs/limits.go:76,107`, `app/controllers/job_controller.go:179`, `app/jobs/hooks.go:197`.

Impact: money only. The 24-hour quota counts created jobs, but `Retry` re-renders (and re-calls the paid model) up to `MaxAttempts` (5) per job without touching the quota: up to 100 calls per account per day instead of 20. Sign-in is open to any Google account and there is no aggregate budget, so accounts multiply it. Each call is capped by `STUDIO_MAX_JOB_COST_CENTS` only.

Reproduction: source trace; with the quota exhausted, `Retry` still passes `Requeue`.

Fix (owner decision, not implemented): count renders in the same locked window, and add a global daily budget or an allow-list.

### ST-SEC-003, Low, CWE-362

`app/controllers/job_controller.go:246-291`, `app/jobs/render.go:321-337`.

Impact: the job owner can undo a claim (status back to `ready`, attempts back down), which weakens `MaxAttempts` and lets two renders share one directory. Only the owner's own job is affected, and the race is narrow.

Cause: `Pack` and the worker `Save` write the whole row with `orm.Update` after reading it earlier. The repository rule requires conditional updates for claim state.

Reproduction (local): load a `ready` job with attempts 1, `Requeue` and `Claim` it, then `orm.Update` the stale row. The row ends `status=ready attempts=1`.

Fix: column-scoped updates.

### ST-SEC-005, Low, CWE-1188

`routes/auth.go:390-407`.

Impact: surface only. `/register`, `/login`, `/forgot-password` and `/reset-password` stay live although the studio rules say login is Google-only. They add credential stuffing, mail sending and account farming surface; each is throttled and a verified email is still needed before jobs.

Fix (owner decision, not implemented): remove the routes and the scaffold tests that cover them.

### ST-SEC-006, Low, CWE-61

`railway.app.toml:11`.

Impact: after code execution as the app user, a symlink planted in `/app/storage` makes the next boot, which runs as root, change the owner of an arbitrary container file (BusyBox `chown` dereferences symlinks by default). Container-local only.

Reproduction: code-path argument, not executed.

Fix: `chown` only the mount point, then `find -xdev ... chown -h` for entries with another owner.

### ST-SEC-007, needs validation

`Dockerfile.app:46-50`. The image defaults `MAIL_MAILER=log`, which writes reset and verification links to the JSON log. Blocked on the deployed `MAIL_MAILER` value and on who can read Railway logs. Owner check: the `studio-app` variable should be `resend` or `smtp`.

## Rejected candidates

- ST-SEC-R01, ASS override tags on the spoken path: ffmpeg's SRT-to-ASS conversion strips the backslashes (`{\an8\fs120}` became `{n8s120}`), so only the `\anN` position tag survives. No impact shown.
- ST-SEC-R02, ffmpeg playlist demuxer through the upload: the upload must start with a RIFF/WAVE signature, so the WAV demuxer is selected.
- ST-SEC-R03, docs server path traversal: `resolveRequest` confines every decoded path and has tests.

Reviewed without finding: owner filter on every `/jobs/{job}` route (`find` scopes by `user_id`), download and captions names (fixed by the server), ffmpeg and renderer argument lists and `commandCtx` deadlines, caption validation on the plan shots, model reply cap and key handling (`postJSON` drops provider bodies), Google account linking (verified email only, state in cache), `composition.html` escaping, Inertia pages (no raw HTML sinks), CI (actions pinned by SHA, scoped tokens, inputs passed through `env`), Dockerfile base images pinned, no secrets in git history (sampled).
