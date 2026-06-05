# syntax=docker/dockerfile:1.4
FROM node:22-alpine
WORKDIR /app/apps/miniapp

COPY apps/miniapp/package.json ./
RUN npm install

COPY apps/miniapp/ ./

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
