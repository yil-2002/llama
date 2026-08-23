# O'rnatish Qo'llanmasi

## Talablar

- Ubuntu 22.04/24.04 LTS
- Docker va Docker Compose
- 2GB+ RAM
- Telegram Bot Token (BotFather'dan)

## Bosqichma-bosqich o'rnatish

### 1. BotFather'dan token olish

1. [@BotFather](https://t.me/BotFather) ga kiring
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username bering
4. Tokenni nusxa oling

### 2. (Ixtiyoriy) Kunlik hisobot/alert uchun sobit chat ID

Bot kirish uchun rol yoki ID talab qilmaydi - faqat umumiy parol
ishlatiladi (pastga qarang). Agar kunlik hisobot/alertlarni bitta sobit
chatga yuborishni istasangiz (aks holda ular barcha faol sessiyalarga
yuboriladi), [@userinfobot](https://t.me/userinfobot) orqali ID'ingizni
oling va `TELEGRAM_SUPERADMIN_ID` ga qo'ying.

### 3. Bir qatorli o'rnatish

```bash
curl -fsSL https://raw.githubusercontent.com/1jehuang/vps-master-bot/main/scripts/install.sh | sudo bash
```

### 4. Qo'lda o'rnatish

```bash
# 1. Repozitoriyni klonlash
git clone https://github.com/1jehuang/vps-master-bot.git
cd vps-master-bot

# 2. Muhit o'zgaruvchilarini sozlash
cp .env.example .env
nano .env   # TELEGRAM_BOT_TOKEN ni kiriting (TELEGRAM_SUPERADMIN_ID ixtiyoriy)

# 3. Kirish paroli hash'ini yaratish
python3 -m venv .venv && source .venv/bin/activate
pip install bcrypt
python -m scripts.gen_password_hash
# Chiqqan BOT_PASSWORD_HASH qatorini .env fayliga qo'ying

# 4. Docker bilan ishga tushirish
docker compose up -d
```

### 5. Birinchi ishga tushirish

1. Botga `/start` yuboring
2. Bot sizdan parolni so'raydi — `.env`dagi `BOT_PASSWORD_HASH` mos keladigan parolni kiriting
3. To'g'ri parol kiritilgach, shu Telegram akkaunt/qurilma uchun sessiya ochiladi (muddati `SESSION_TTL_DAYS` bilan belgilanadi)
4. Bot bitta parolga ega — istalgan akkaunt/qurilmadan xuddi shu parol bilan kirish mumkin. Boshqa hech kim parolni bilmasa kira olmaydi
5. `/logout` — joriy kirishni yakunlaydi, `/sessions` — barcha faol kirishlarni ko'rsatadi

## Muammolar

**Bot javob bermayapti?**
```bash
docker logs -f vps-master-bot
```

**Docker ruxsat muammosi?**
```bash
sudo usermod -aG docker $USER
# Logout va qayta kiring
```
