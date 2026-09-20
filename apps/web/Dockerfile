# =============================================================================
# OntDekker — Frontend Dockerfile (Next.js 14)
#
# Multi-stage build:
#   1. deps      — install ALL dependencies (dev + prod) needed for the build
#   2. builder   — build the Next.js production bundle
#   3. runner    — minimal runtime image (prod deps + compiled output only)
# =============================================================================

# --- Stage 1: Install ALL dependencies (dev + prod) -------------------------
#
# devDependencies such as tailwindcss, postcss, typescript, and
# eslint-config-next are required at build time by `npm run build`.
# Using plain `npm ci` (without --only=production) installs everything.
# The runner stage below only copies what is needed at runtime, so the
# final image stays lean regardless.
FROM node:20-alpine AS deps
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# --- Stage 2: Build the application ----------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app

# Copy ALL deps (including devDeps) from the previous stage
COPY --from=deps /app/node_modules ./node_modules
# Copy all source files (build context is apps/web, so . is the web root)
COPY . .

# Build the Next.js production bundle
RUN npm run build

# --- Stage 3: Minimal runtime image ----------------------------------------
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root user for security
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# Copy only the runtime artefacts from the builder stage.
# Note: this project has no public/ directory, so that copy is omitted.
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.mjs ./next.config.mjs

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["npm", "run", "start"]
