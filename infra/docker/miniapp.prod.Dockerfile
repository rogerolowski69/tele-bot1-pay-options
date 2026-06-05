# syntax=docker/dockerfile:1.4
# Production Mini App — static Vite build + nginx (Railway / production)
FROM node:22-alpine AS build
WORKDIR /app
COPY apps/miniapp/package.json ./
RUN npm install

COPY apps/miniapp/ ./
RUN npm run build

FROM nginx:1.27-alpine

COPY infra/docker/nginx.miniapp.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

ENV PORT=8080
ENV API_UPSTREAM=http://localhost:8000

EXPOSE 8080

# nginx:alpine entrypoint runs envsubst on templates, then starts nginx
