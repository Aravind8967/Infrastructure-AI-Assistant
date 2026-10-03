# Stage 1: Build Vite + React frontend
FROM node:20-alpine AS build

WORKDIR /app

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm ci

# Copy frontend source code and build production bundle
COPY . .
RUN npm run build

# Stage 2: Serve built assets with Nginx
FROM nginx:alpine

# Copy built frontend assets from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Copy Nginx reverse proxy configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
