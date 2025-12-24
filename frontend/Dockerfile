# Build Stage - Base Image aus lokaler GitLab Registry
FROM registry.newsxc.net/darthvaper/docker-proxmox-commander/node:20-alpine AS build

WORKDIR /app

# Dependencies installieren
COPY package*.json ./
RUN npm install

# App bauen
COPY . .
RUN npm run build

# Production Stage - Base Image aus lokaler GitLab Registry
FROM registry.newsxc.net/darthvaper/docker-proxmox-commander/nginx:alpine

# Nginx Config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Built Files kopieren
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
