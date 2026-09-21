FROM node:22-alpine AS build
WORKDIR /frontend
COPY frontend/package.json ./
# No fabricated lockfile is shipped. npm install resolves one during the build.
RUN npm install
COPY frontend/ ./
RUN npm run build
FROM nginxinc/nginx-unprivileged:stable-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /frontend/dist /usr/share/nginx/html
EXPOSE 8080
