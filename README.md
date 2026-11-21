# Owly English — ingliz tili Telegram bot + Mini App

O'zbeklar uchun ingliz tilida gaplashish murabbiyi: AI bilan erkin suhbat, IELTS Speaking mock
(Part 1-3), band ball va **o'zbekcha izohli** feedback. Maskot — boyo'g'li **Owly**.

## Nimalar bor (MVP)

| Qism | Holat |
|---|---|
| Bot: `/start`, matnli va ovozli suhbat, `/feedback`, `/premium` | ✅ |
| Mini App: onboarding (maqsad + daraja), suhbat (matn + mikrofon), natija, progress | ✅ |
| AI suhbat va IELTS baholash (DeepSeek, model sozlamadan almashtiriladi) | ✅ |
| Ovoz: STT/TTS provayderi `.env` orqali (OpenAI-mos `/audio` API) | ✅ interfeys |
| Bepul limit (kuniga N xabar), 3 kunlik sinov, streak | ✅ |
| To'lov: Telegram Stars oylik obuna | ✅ |
| To'lov: Click / Payme (tashqi sayt) | 🔌 modul tayyor, MChJ/YaTT kalitlari kerak |
| Dashboard: faollik soat va daraja bo'yicha (bot `/stats` + Mini App) | ✅ |
| Maskot stikerlari (bot chatida TGS, Mini App'da SVG animatsiya) | ✅ SVG; TGS file_id `.env` ga |

## Arxitektura

```
Telegram ──► bot (aiogram) ─┐
Mini App ──► api (FastAPI) ─┼─► Redis navbati (arq) ─► worker × N ─► DeepSeek / STT / TTS
                            └─► PostgreSQL ◄───────────────┘
```

- **api** — tez javob beradi, og'ir ishlarni (LLM, STT, TTS) navbatga qo'yadi.
- **worker** — navbatdagi ishlarni bajaradi. 10 000 obunachi uchun 2-4 ta worker yetarli,
  kerak bo'lsa `docker compose up -d --scale worker=6`.
- **bot** — long polling; foydalanuvchi bot chatida ham to'g'ridan-to'g'ri gaplasha oladi.

## Ishga tushirish

```bash
cp .env.example .env     # BOT_TOKEN, WEBAPP_URL, LLM_API_KEY, ADMIN_IDS ni to'ldiring
docker compose up -d --build
```

Mini App `http://server:8080` da ishlaydi. Uni HTTPS orqali (masalan, Caddy/Nginx + Let's Encrypt)
oching va @BotFather → Bot Settings → Menu Button ga shu manzilni qo'ying.

### Lokal ishlab chiqish (Docker'siz)

```bash
cd backend
pip install -r requirements-dev.txt
pytest                                   # testlar
QUEUE_MODE=inline DATABASE_URL=sqlite+aiosqlite:///dev.db uvicorn app.main:app --reload
QUEUE_MODE=inline DATABASE_URL=sqlite+aiosqlite:///dev.db python -m bot.main

cd ../webapp && npm install && npm run dev   # /api localhost:8000 ga proksi qilinadi
```

`QUEUE_MODE=inline` — Redis'siz, ishlar shu jarayonda bajariladi (faqat lokal uchun).

## AI modelni almashtirish

- `.env`: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` (istalgan OpenAI-mos API: DeepSeek, OpenRouter va h.k.)
- Ishlab turgan botda: admin `/model` (joriyini ko'rish) va `/setmodel <nom>` — qayta deploy kerak emas.

## To'lov

Telegram qoidasiga ko'ra bot va Mini App ichida raqamli obuna **faqat Stars** bilan sotiladi.
Shuning uchun:

1. **Hozir:** `PAYMENT_PROVIDERS=stars`. `/premium` va Mini App'dagi tugma 30 kunlik Stars obunasini ochadi,
   Telegram har oy avtomatik yechadi. To'lov `successful_payment` orqali bir marta (idempotent) qayd etiladi.
2. **MChJ/YaTT tayyor bo'lgach:** `PAYMENT_PROVIDERS=stars,click,payme` va `CLICK_*`, `PAYME_*` kalitlari.
   Click/Payme faqat Telegramdan tashqaridagi saytda ko'rsatiladi (`in_telegram=False`), Mini App ularni
   yashiradi. Qolgan ish: tashqi to'lov sahifasi va Click/Payme webhook'lari
   (`backend/app/payments/external.py` dagi izohga qarang). Webhook muvaffaqiyatli bo'lsa
   `record_payment(...)` chaqiriladi.

Yangi provayder qo'shish: `PaymentProvider` protokolini amalga oshirib, `register_provider("nom", Klass)`.

## Dashboard

- Bot: admin `/stats` yoki `/stats 30` — matnli grafik.
- Mini App: bosh sahifada adminlarga **📊 Dashboard** tugmasi chiqadi.
- Ko'rsatkichlar: jami / faol / yangi foydalanuvchilar, premium, Stars tushumi,
  **soat bo'yicha faollik** (Toshkent vaqti) va **daraja (CEFR) bo'yicha** foydalanuvchi va xabarlar.

## Keyingi qadamlar

- Alembic migratsiyalari (hozir jadvallar ishga tushganda yaratiladi)
- Kunlik eslatma (streak saqlash uchun) va referal tizim
- Owly'ning TGS animatsion stikerlar to'plami
- Click/Payme tashqi sayt va webhook'lar
