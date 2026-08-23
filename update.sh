#!/bin/bash
set -e

INSTALL_DIR="/opt/vps-master-bot"
cd "$INSTALL_DIR"

echo "🔄 Yangilanmoqda..."

# Joriy ma'lumotlarni zaxiralash
tar -czf "backups/pre-update-$(date +%Y%m%d_%H%M%S).tar.gz" data/ .env

# So'nggi o'zgarishlarni yuklash
git pull origin main 2>/dev/null || echo "Git yangilanmadi, qo'lda tekshiring."

# Qayta yig'ish va ishga tushirish
docker compose down
docker compose pull
docker compose up -d --build

echo "✅ Yangilash muvaffaqiyatli!"
