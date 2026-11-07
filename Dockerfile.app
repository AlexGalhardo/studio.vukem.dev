# Production image: Vite assets, a static Go binary, a small non-root runtime.
# Railway, Fly, Render and plain Docker build it as is:
# https://vukem.dev/docs/deployment/docker-and-railway

FROM oven/bun:1.4.4-alpine AS assets
WORKDIR /src
COPY package.json bun.lock* ./
# The lockfile is a required build input: the image installs exactly the
# versions the repository tracks. Without one npm and pnpm refuse, while bun
# and yarn resolve fresh versions and say nothing, so the requirement is
# stated here and is the same for every package manager. Generate it with
# "bun install" and commit it; .dockerignore must not exclude it.
RUN if ! ls bun.lock* >/dev/null 2>&1; then \
		echo "bun.lock not found: run 'bun install', commit it, then build again" >&2; \
		exit 1; \
	fi \
	&& bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM golang:1.27.3-alpine3.24 AS build
WORKDIR /src
ENV CGO_ENABLED=0
COPY go.mod go.sum ./
RUN go mod download
COPY . .
COPY --from=assets /src/resources/public/build resources/public/build
# Same tags as vukem build: .buildtags lists them (one per line or
# comma-separated, "#" comments); --minimal apps put vukem_nosqlite there.
RUN tags="$(sed 's/#.*//' .buildtags 2>/dev/null | tr -s ', \t\r\n' ',' | sed 's/^,//; s/,$//')" \
	&& go build -trimpath -ldflags="-s -w" -tags "$tags" -o /out/app ./cmd/app

# Only the SKILL files ship: the prompt compiler reads them, the kits' assets
# and scripts stay out of the image.
FROM alpine:3.24.3 AS skills
COPY .agents/skills /in
RUN mkdir /out && cd /in && find . \( -name SKILL.md -o -name SKILL.en.md \) | tar cf - -T - | tar xf - -C /out

FROM alpine:3.24.3
RUN apk add --no-cache ca-certificates tzdata ffmpeg font-dejavu \
	&& adduser -D -H -u 10001 app \
	&& mkdir -p /app/storage \
	&& chown app:app /app/storage
WORKDIR /app
COPY --from=build /out/app /app/app
COPY --from=skills /out /app/.agents/skills
USER app
# The platform's PORT overrides this one; HOST=0.0.0.0 makes the server
# reachable from outside the container. Pass secrets at runtime, never here.
# The app sends no mail: sign-in is Google only and no route builds a mailer.
# MAIL_MAILER=log stays as a no-op default (it only writes to the log) so the
# framework never stops at boot for a missing mailer; no message exists to log.
# The app owns a `jobs` table (render jobs), so the vukem database queue uses queue_jobs/queue_failed_jobs.
# QUEUE_CONNECTION=database lets serve run the render worker beside the web
# server; the default sync would render inside the request.
ENV APP_ENV=production HOST=0.0.0.0 PORT=3000 LOG_FORMAT=json MAIL_MAILER=log \
	QUEUE_CONNECTION=database QUEUE_TABLE=queue_jobs QUEUE_FAILED_TABLE=queue_failed_jobs \
	STUDIO_STORAGE=/app/storage/renders
# A platform start command (Railway, Fly) replaces this entrypoint, so it has
# to name the binary: "/app/app queue:work", never "queue:work".
EXPOSE 3000
ENTRYPOINT ["/app/app"]
