WELCOME = (
    "Salom, {name}! 🦉 Men <b>Owly</b> — ingliz tilida gaplashish bo'yicha do'stingman.\n\n"
    "• Menga inglizcha yozing yoki <b>ovozli xabar</b> yuboring — suhbatlashamiz\n"
    "• /feedback — suhbat bo'yicha IELTS band ball va o'zbekcha izoh\n"
    "• Mini App'da IELTS Speaking mock, progress va boshqalar\n\n"
    "Bugun bepul: {free} ta xabar."
)
OPEN_APP = "📱 Mini App'ni ochish"
LIMIT_REACHED = (
    "Bugungi bepul limit tugadi 😔\n"
    "Premium bilan cheksiz gaplashing va IELTS mock'larni oching: /premium"
)
NO_STT = "Ovozli xabarlar hozircha sozlanmagan. Iltimos, matn yozing ✍️"
THINKING = "🦉 o'ylayapman..."
NO_CHAT = "Avval biror narsa yozing yoki ovozli xabar yuboring, keyin /feedback bosing."
FEEDBACK_WAIT = "📝 Javoblaringizni baholayapman, biroz kuting..."
ERROR = "Kechirasiz, xatolik yuz berdi. Birozdan keyin qayta urinib ko'ring."
PAID = "🎉 Rahmat! Premium {date} gacha faol. Cheksiz suhbat va IELTS mock ochildi!"
PREMIUM_INFO = (
    "⭐ <b>Owly Premium</b>\n"
    "• Cheksiz AI suhbat (matn va ovoz)\n"
    "• IELTS Speaking Part 1-3 mock va band ball\n"
    "• Batafsil o'zbekcha feedback\n\n"
    "Narx: {price} Stars / 30 kun (har oy avtomatik yangilanadi)"
)
CRITERIA = {
    "fluency": "Ravonlik",
    "lexical": "Lug'at",
    "grammar": "Grammatika",
    "pronunciation": "Talaffuz",
}


def format_feedback(fb: dict) -> str:
    scores = fb.get("scores", {})
    lines = [f"🏁 <b>Umumiy band: {fb.get('overall_band', '—')}</b>", ""]
    for key, title in CRITERIA.items():
        if key in scores:
            lines.append(f"• {title}: <b>{scores[key]}</b>")
    if fb.get("summary_uz"):
        lines += ["", fb["summary_uz"]]
    mistakes = fb.get("mistakes") or []
    if mistakes:
        lines += ["", "<b>Xatolar:</b>"]
        for m in mistakes[:6]:
            lines.append(f"❌ <i>{_esc(m.get('original', ''))}</i>\n✅ {_esc(m.get('better', ''))}\n💡 {_esc(m.get('explanation_uz', ''))}")
    if fb.get("next_steps_uz"):
        lines += ["", "<b>Keyingi qadam:</b>", *[f"➡️ {_esc(s)}" for s in fb["next_steps_uz"]]]
    return "\n".join(lines)


def _esc(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
