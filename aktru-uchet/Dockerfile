FROM node:22-bookworm-slim

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 make g++ \
  && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY auth.js db.js mail.js server.js warehouse.js ./
COPY public ./public
COPY scripts ./scripts

ENV NODE_ENV=production
ENV PORT=3847
ENV DB_PATH=/data/aktru.db

EXPOSE 3847
CMD ["node", "server.js"]
