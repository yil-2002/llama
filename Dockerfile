# Ko'p bosqichli build
FROM python:3.11-slim as builder

WORKDIR /app

# Build bog'liqliklarini o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python bog'liqliklarini o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime bosqichi
FROM python:3.11-slim

WORKDIR /app

# Runtime bog'liqliklari
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wireguard-tools \
    qrencode \
    systemd \
    sudo \
    cron \
    nginx \
    certbot \
    python3-certbot-nginx \
    postgresql-client \
    default-mysql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Root bo'lmagan foydalanuvchi yaratish
RUN groupadd -r vpsbot && useradd -r -g vpsbot -s /bin/bash vpsbot \
    && mkdir -p /app/data /app/logs /app/backups \
    && chown -R vpsbot:vpsbot /app

# Python paketlarini builder'dan nusxa olish
COPY --from=builder /root/.local /home/vpsbot/.local
ENV PATH=/home/vpsbot/.local/bin:$PATH

# Ilova kodini nusxa olish
COPY --chown=vpsbot:vpsbot bot/ ./bot/
COPY --chown=vpsbot:vpsbot config/ ./config/
COPY --chown=vpsbot:vpsbot scripts/ ./scripts/

# Root bo'lmagan foydalanuvchiga o'tish
USER vpsbot

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Kirish nuqtasi
CMD ["python", "-m", "bot.main"]
