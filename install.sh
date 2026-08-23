#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}VPS Master Bot o'rnatuvchisi${NC}"
echo "========================================"

# Root tekshirish
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Iltimos, root huquqlari bilan ishga tushiring: sudo bash install.sh${NC}"
    exit 1
fi

# Docker o'rnatish
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker o'rnatilmoqda...${NC}"
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}Docker Compose o'rnatilmoqda...${NC}"
    apt-get install -y docker-compose-plugin
fi

# Papkalarni yaratish
INSTALL_DIR="/opt/vps-master-bot"
mkdir -p "$INSTALL_DIR"/{data,logs,backups}
cd "$INSTALL_DIR"

# Repozitoriy yuklash
if [ ! -d "$INSTALL_DIR/.git" ]; then
    echo -e "${YELLOW}Repozitoriy yuklanmoqda...${NC}"
    git clone https://github.com/1jehuang/vps-master-bot.git . 2>/dev/null || {
        echo -e "${YELLOW}Git clone muvaffaqiyatsiz. Fayllar nusxa olinmoqda...${NC}"
    }
fi

# .env yaratish
if [ ! -f "$INSTALL_DIR/.env" ]; then
    echo -e "${YELLOW}.env fayli yaratilmoqda...${NC}"
    cp .env.example .env

    echo ""
    read -p "Telegram Bot Tokenni kiriting (BotFather'dan olingan): " BOT_TOKEN
    read -p "Kunlik hisobot/alert uchun sobit chat ID (ixtiyoriy, Enter bosib o'tkazib yuborishingiz mumkin): " ADMIN_ID

    sed -i "s|your_bot_token_from_botfather|$BOT_TOKEN|g" .env
    if [ -n "$ADMIN_ID" ]; then
        sed -i "s,^TELEGRAM_SUPERADMIN_ID=.*,TELEGRAM_SUPERADMIN_ID=$ADMIN_ID," .env
    fi

    echo -e "${GREEN}.env sozlandi!${NC}"

    # Botga kirish paroli (MAJBURIY - botga kirishning yagona yo'li shu)
    echo ""
    BOT_PASSWORD=""
    while [ -z "$BOT_PASSWORD" ]; do
        read -s -p "Botga kirish uchun parol o'rnating (bo'sh bo'lishi mumkin emas): " BOT_PASSWORD
        echo ""
    done
    if ! python3 -c "import bcrypt" 2>/dev/null; then
        pip3 install --quiet --break-system-packages bcrypt 2>/dev/null || pip3 install --quiet bcrypt
    fi
    PASSWORD_HASH=$(python3 -c "import bcrypt,sys; print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt()).decode())" "$BOT_PASSWORD")
    # '|' bo'lishi mumkin bo'lgan belgilardan xoli bo'lgani uchun ',' ajratuvchi sifatida ishlatiladi
    sed -i "s,^BOT_PASSWORD_HASH=.*,BOT_PASSWORD_HASH=$PASSWORD_HASH," .env
    echo -e "${GREEN}Parol saqlandi.${NC}"
fi

# Ollama so'rash
read -p "Ollama AI xizmatini o'rnatishni xohlaysizmi? (y/n): " INSTALL_OLLAMA

if [ "$INSTALL_OLLAMA" = "y" ] || [ "$INSTALL_OLLAMA" = "Y" ]; then
    echo -e "${YELLOW}Bot va Ollama ishga tushirilmoqda...${NC}"
    docker compose --profile ai up -d
else
    echo -e "${YELLOW}Bot faqat ishga tushirilmoqda...${NC}"
    docker compose up -d
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}O'rnatish muvaffaqiyatli yakunlandi!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Bot loglari: docker logs -f vps-master-bot"
echo "Botni to'xtatish: docker compose down"
echo "Botni qayta ishga tushirish: docker compose restart"
echo ""
echo -e "${YELLOW}Eslatma: Agar Docker buyruqlari ishlamasa,${NC}"
echo -e "${YELLOW}logout qilib, qayta kiring (groups yangilanishi uchun).${NC}"
