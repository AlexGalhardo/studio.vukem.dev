# Docs site (https://studio.vukem.dev): Astro static build served by a small
# Node-compatible server. The app image is Dockerfile.app.
FROM oven/bun:1.4.4-alpine AS build
WORKDIR /src/site

COPY site/package.json site/package-lock.json ./
RUN bun install

COPY site/ ./
COPY CHANGELOG.md /src/CHANGELOG.md

ENV SITE_URL=https://studio.vukem.dev
RUN bun run build

FROM oven/bun:1.4.4-alpine AS run
WORKDIR /app/site
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000

COPY --from=build --chown=bun:bun /src/site/dist ./dist
COPY --from=build --chown=bun:bun /src/site/scripts/serve.ts ./scripts/serve.ts

USER bun
EXPOSE 3000
CMD ["bun", "scripts/serve.ts"]
