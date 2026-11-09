# Site estático do portfólio: o Python gera o HTML a partir de content/ e templates/; o nginx sem privilégios serve (porta 8080).
FROM python:3.12-slim AS build
WORKDIR /site
COPY requirements-build.txt .
RUN pip install --no-cache-dir -r requirements-build.txt
COPY build.py ./
COPY content content
COPY templates templates
COPY assets assets
RUN python build.py --out /site/dist

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=build /site/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1:8080/ || exit 1
