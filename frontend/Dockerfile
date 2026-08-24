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
# 18 Ağu 2026'da bulundu: bu ARG hiç geçirilmiyordu, SITE_URL kodda
# "https://nexstream.news" (satın alınmamış, kimseye ait olmayan bir domain)
# varsayılanına düşüyordu — robots.txt/sitemap.xml/OG meta hepsi YANLIŞ
# domain'e işaret ediyordu, canlıda hiç fark edilmemişti.
ARG NEXT_PUBLIC_SITE_URL=https://nexstreamnewsengine.duckdns.org
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
# Kullanım analitiği (v2.4) — boş bırakılırsa AnalyticsProvider tamamen no-op
# kalır (bkz. components/AnalyticsProvider.tsx), diğer opsiyonel entegrasyonlarla
# aynı desen.
ARG NEXT_PUBLIC_POSTHOG_KEY=""
ENV NEXT_PUBLIC_POSTHOG_KEY=$NEXT_PUBLIC_POSTHOG_KEY
ARG NEXT_PUBLIC_POSTHOG_HOST="https://us.i.posthog.com"
ENV NEXT_PUBLIC_POSTHOG_HOST=$NEXT_PUBLIC_POSTHOG_HOST
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
