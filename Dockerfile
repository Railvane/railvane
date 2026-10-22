# Stage 1: build the UI into railvane/static
FROM node:24-alpine AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY web/ ./
RUN npm run build

# Stage 2: small runtime — Python + git, no database
FROM python:3.13-alpine
# safe.directory: mounted repositories are owned by another user (host, CI runner).
# autocrlf=input + filemode=false: Windows checkouts (CRLF, no exec bit) must not look modified.
# apk upgrade: take the latest security patches of the base image on every build.
RUN apk upgrade --no-cache \
 && apk add --no-cache git \
 && git config --system --add safe.directory "*" \
 && git config --system core.autocrlf input \
 && git config --system core.filemode false \
 && adduser -D -u 1000 railvane \
 && mkdir -p /home/railvane/.cache/railvane /data \
 && chown -R railvane:railvane /home/railvane/.cache /data
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY railvane/ railvane/
COPY --from=web /src/railvane/static railvane/static
# pip is only needed to install: remove it (and the ensurepip wheel). Its vendored copies of certifi,
# urllib3, msgpack and setuptools are the image's only known CVEs, and nothing uses pip at runtime.
RUN pip install --no-cache-dir . && rm -rf /app/railvane \
 && pip uninstall -y pip \
 && rm -rf /usr/local/lib/python3.*/ensurepip

USER railvane
# /data: instance id and hub link only (webheaven-kit), never content
ENV RAILVANE_DATA=/data
VOLUME /workspace /data
EXPOSE 8484
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8484/api/health')"
CMD ["railvane", "serve", "/workspace", "--host", "0.0.0.0", "--port", "8484"]
