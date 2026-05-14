# syntax=docker/dockerfile:1.7
# Web service: build with Bun, serve via `bun run preview` (vite preview).

FROM oven/bun:1.1-alpine

WORKDIR /web

COPY package.json package-lock.json* bun.lockb* ./
RUN bun install

COPY . .
RUN bun run build

ENV PORT=4173 \
    VITE_API_URL=http://api:8000

EXPOSE 4173
CMD ["bun", "run", "preview"]
