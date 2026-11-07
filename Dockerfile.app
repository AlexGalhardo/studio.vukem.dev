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

# Only the SKILL.md files ship: the style catalog reads them, the kit assets
# and scripts stay out of the image.
FROM alpine:3.24.2 AS skills
COPY .agents/skills /in
RUN mkdir /out && cd /in && find . -name SKILL.md | tar cf - -T - | tar xf - -C /out

FROM alpine:3.24.2
# ffmpeg and ffprobe render and check the MP4; font-dejavu gives drawtext a font.
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
# MAIL_MAILER=log keeps the image runnable: with APP_ENV=production an unset
# mailer stops every command at boot, serve and `about` alike, as soon as a
# route needs one. "log" writes each message to the JSON log, so nothing is
# lost silently; set smtp, resend or mailtrap on the deploy to send for real.
# QUEUE_CONNECTION=database lets serve run the render worker next to the web
# server; with the default sync a render would block the request.
ENV APP_ENV=production HOST=0.0.0.0 PORT=3000 LOG_FORMAT=json MAIL_MAILER=log \
	QUEUE_CONNECTION=database \
	STUDIO_SKILLS_DIR=/app/.agents/skills \
	STUDIO_OUTPUT_DIR=/app/storage/videos \
	STUDIO_FONT_FILE=/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf
# A platform start command (Railway, Fly) replaces this entrypoint, so it has
# to name the binary: "/app/app queue:work", never "queue:work".
EXPOSE 3000
ENTRYPOINT ["/app/app"]
