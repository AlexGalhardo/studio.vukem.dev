FROM oven/bun:1.4.4-alpine AS build
WORKDIR /src/site

COPY site/package.json site/package-lock.json ./
RUN bun install

COPY site/ ./
COPY CHANGELOG.md /src/CHANGELOG.md

ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_SITE_URL=https://studio.vukem.dev
RUN bun run build

FROM oven/bun:1.4.4-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=3000

COPY --from=build --chown=bun:bun /src/site/.next/standalone ./
COPY --from=build --chown=bun:bun /src/site/.next/static ./.next/static
COPY --from=build --chown=bun:bun /src/site/public ./public

USER bun
EXPOSE 3000
CMD ["bun", "server.js"]
