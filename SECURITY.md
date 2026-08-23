# Xavfsizlik Qo'llanmasi

## Asosiy tamoyillar

1. **Bot root sifatida ishlamaydi** - `vpsbot` foydalanuvchisi
2. **Har bir buyruq logga yoziladi** - audit trail
3. **Xavfli buyruqlar bloklangan** - `rm -rf`, `dd`, `mkfs`
4. **Path traversal himoyasi** - `..` va symlink tekshiruvi
5. **Rate limiting** - 20 buyruq/daqiqa

## Tavsiyalar

- `.env` faylini hech kimga ko'rsatmang (u `BOT_PASSWORD_HASH`ni saqlaydi)
- Kuchli, uzun parol tanlang - bot bitta umumiy parolga tayanadi
- `/sessions` orqali vaqti-vaqti bilan faol kirishlarni tekshiring, notanish sessiyani `Yakunlash` bilan yoping
- Shubha tug'ilsa `/change_password` bo'yicha yo'riqnomaga amal qilib parolni yangilang - bu barcha eski sessiyalarni avtomatik yakunlaydi
- Muntazam loglarni tekshiring
- Zaxiralarni muntazam yaratib turing
