# syntax=docker/dockerfile:1

# Build context is the repo root (same convention as apps/api):
#   scripts/docker-build.sh web   (same as: docker build -f apps/web/Dockerfile -t taipan-web .)
# Run:
#   docker run --rm -p 3000:3000 -e API_INTERNAL_URL=http://api:8000 taipan-web

FROM node:24-alpine AS base
ENV PNPM_HOME=/pnpm
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

FROM base AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/pnpm-lock.yaml apps/web/pnpm-workspace.yaml apps/web/
# cd, not -C: corepack resolves packageManager from cwd's package.json.
WORKDIR /app/apps/web
RUN pnpm install --frozen-lockfile

FROM base AS build
WORKDIR /app
COPY --from=deps /app/apps/web/node_modules apps/web/node_modules
COPY apps/web apps/web
RUN cd apps/web && pnpm build

FROM node:24-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S nodejs && adduser -S nextjs -G nodejs
COPY --from=build --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/apps/web/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/apps/web/public ./public
USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
