"""Git server handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Messages
from bot.utils import log_execution
from bot.keyboards import get_back_keyboard, get_git_menu_keyboard
from bot.services import GiteaService

gitea = GiteaService()


@log_execution("gitea")
async def gitea_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/gitea buyrug'i."""
    if not update.effective_message:
        return

    if not settings.is_gitea_enabled:
        await update.effective_message.reply_text(Messages.SERVICE_DISABLED.format(service="Gitea"))
        return

    await update.effective_message.reply_text(
        "📦 <b>Gitea Git Server</b>\n\nKerakli amalni tanlang:",
        reply_markup=get_git_menu_keyboard(),
        parse_mode="HTML",
    )


async def git_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Git callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    if not settings.is_gitea_enabled:
        await query.edit_message_text(Messages.SERVICE_DISABLED.format(service="Gitea"), reply_markup=get_back_keyboard())
        return

    data = query.data.split(":")
    action = data[1] if len(data) > 1 else ""

    if action == "repos":
        repos = await gitea.list_repos()
        if not repos:
            await query.edit_message_text("📭 Repositoriyalar yo'q.", reply_markup=get_back_keyboard())
            return
        lines = []
        for repo in repos[:10]:
            name = repo.get("name", "Noma'lum")
            stars = repo.get("stars_count", 0)
            private = "🔒" if repo.get("private") else "🌐"
            lines.append(f"{private} <b>{name}</b> ⭐ {stars}")
        text = "📦 <b>Repositoriyalar</b>\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")

    elif action == "create_repo":
        await query.edit_message_text(
            "📝 <b>Yangi repositoriya nomini kiriting:</b>",
            reply_markup=get_back_keyboard(),
            parse_mode="HTML",
        )
        context.user_data["awaiting_repo_name"] = True

    elif action == "users":
        users = await gitea.list_users()
        if not users:
            await query.edit_message_text("📭 Foydalanuvchilar yo'q.", reply_markup=get_back_keyboard())
            return
        lines = [f"👤 <b>{u.get('login', 'Noma\'lum')}</b> ({u.get('full_name', '')})" for u in users[:10]]
        text = "👥 <b>Foydalanuvchilar</b>\n\n" + "\n".join(lines)
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


def register_git_handlers(application) -> None:
    application.add_handler(CommandHandler("gitea", gitea_command))
    application.add_handler(CallbackQueryHandler(git_callback, pattern="^git:"))
