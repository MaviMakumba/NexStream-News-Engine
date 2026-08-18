FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
ENV PORT=3000
# Docker her container'a otomatik HOSTNAME=<container-id> koyar; Next.js standalone
# server.js buna bind eder ve o isim TEK bir ağ arayüzüne çözülür. Bu container iki
# ağda (frontend + backend) olduğu için nginx diğer ağdan bağlanamaz → 502.
# 28 Tem 2026 deploy'unda tam olarak bu yaşandı (nginx 172.20.0.5'e gitti,
# Next.js 172.18.0.12'de dinliyordu).
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
