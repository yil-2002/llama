"""Docker boshqaruv handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.constants import Emoji, Messages
from bot.keyboards import get_back_keyboard, get_docker_menu_keyboard
from bot.services import DockerService
from bot.utils import log_execution, escape_html, truncate_text

docker = DockerService()


@log_execution("docker")
async def docker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/docker buyrug'i."""
    if not update.effective_message:
        return
    await update.effective_message.reply_text(
        "🐳 <b>Docker Boshqaruvi</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_docker_menu_keyboard(),
        parse_mode="HTML",
    )


@log_execution("docker_ps")
async def docker_ps_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/docker_ps buyrug'i."""
    if not update.effective_message:
        return

    containers = await docker.list_containers(all_containers=False)
    if not containers:
        await update.effective_message.reply_text("📭 Ishlayotgan konteynerlar yo'q.")
        return

    lines = []
    for c in containers:
        status = Emoji.ACTIVE if c.get("status") == "running" else Emoji.ERROR
        lines.append(
            f"{status} <b>{c['name']}</b>\n"
            f"   🖼 {c['image']}\n"
            f"   🔌 {c.get('ports', 'N/A')}"
        )

    text = "🐳 <b>Ishlayotgan konteynerlar</b>\n\n" + "\n\n".join(lines)
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def docker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Docker callback handler."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    data = query.data.split(":")
    if len(data) < 2:
        return

    action = data[1]

    if action == "running":
        containers = await docker.list_containers(all_containers=False)
        if not containers:
            await query.edit_message_text("📭 Ishlayotgan konteynerlar yo'q.", reply_markup=get_back_keyboard())
            return
        lines = []
        for c in containers:
            lines.append(f"🟢 <b>{c['name']}</b> | {c['image']} | {c.get('ports', '')}")
        text = "🐳 <b>Ishlayotgan konteynerlar</b>\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "stopped":
        containers = await docker.list_containers(all_containers=True)
        stopped = [c for c in containers if c.get("status") != "running"]
        if not stopped:
            await query.edit_message_text("📭 To'xtatilgan konteynerlar yo'q.", reply_markup=get_back_keyboard())
            return
        lines = [f"🔴 <b>{c['name']}</b> | {c['image']}" for c in stopped]
        text = "🐳 <b>To'xtatilgan konteynerlar</b>\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "stats":
        containers = await docker.list_containers(all_containers=False)
        if not containers:
            await query.edit_message_text("📭 Konteinerlar yo'q.", reply_markup=get_back_keyboard())
            return
        lines = []
        for c in containers[:5]:
            stats = await docker.get_container_stats(c["name"])
            if stats.get("success"):
                lines.append(
                    f"📈 <b>{c['name']}</b>\n"
                    f"   🧠 CPU: {stats['cpu_percent']}%\n"
                    f"   💾 RAM: {stats['memory_percent']}%"
                )
        text = "📊 <b>Konteiner statistikasi</b>\n\n" + "\n\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "compose":
        projects = await docker.list_compose_projects()
        if not projects:
            await query.edit_message_text("📭 Docker Compose loyihalari topilmadi.", reply_markup=get_back_keyboard())
            return
        lines = [f"📁 <b>{p['name']}</b>\n   📂 {p['path']}" for p in projects[:10]]
        text = "📝 <b>Docker Compose loyihalari</b>\n\n" + "\n\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


def register_docker_handlers(application) -> None:
    application.add_handler(CommandHandler("docker", docker_command))
    application.add_handler(CommandHandler("docker_ps", docker_ps_command))
    application.add_handler(CallbackQueryHandler(docker_callback, pattern="^docker:"))
