"""AI kod yozish handlerlari."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.config import settings
from bot.constants import Emoji, Messages
from bot.keyboards import get_ai_menu_keyboard, get_back_keyboard
from bot.services import OllamaService
from bot.utils import log_execution, escape_html, truncate_text

ollama = OllamaService()


@log_execution("ai")
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ai <savol> buyrug'i."""
    if not update.effective_message:
        return

    if not context.args:
        await update.effective_message.reply_text(
            "🤖 <b>AI Kod Yordamchi</b>\n\n"
            "Savol berish uchun: <code>/ai Python funksiya yoz</code>",
            reply_markup=get_ai_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    prompt = " ".join(context.args)
    model = settings.ollama_default_model

    # Show loading
    loading_msg = await update.effective_message.reply_text(
        Messages.AI_GENERATING.format(model=model),
        parse_mode="HTML",
    )

    # Generate response
    result = await ollama.generate(prompt, model=model)

    if loading_msg:
        try:
            await loading_msg.delete()
        except Exception:
            pass

    if result.get("success"):
        response = result["response"]
        # Escape HTML but preserve code blocks
        response = escape_html(response)
        text = Messages.AI_RESPONSE.format(response=response)
        text = truncate_text(text, max_length=settings.max_output_length)
        await update.effective_message.reply_text(text, parse_mode="HTML")
    else:
        await update.effective_message.reply_text(
            Messages.ERROR_OCCURRED.format(error=result.get("error", "Noma'lum xatolik")),
            parse_mode="HTML",
        )


@log_execution("ai_model")
async def ai_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ai_model buyrug'i."""
    if not update.effective_message:
        return

    models = await ollama.list_models()
    if not models:
        await update.effective_message.reply_text(Messages.AI_NO_MODELS)
        return

    lines = []
    for model in models:
        name = model.get("name", "Noma'lum")
        size = model.get("size", 0)
        lines.append(f"• {name}")

    text = Messages.AI_MODEL_LIST.format(models="\n".join(lines))
    await update.effective_message.reply_text(text, parse_mode="HTML")


@log_execution("ai_status")
async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/ai_status buyrug'i."""
    if not update.effective_message:
        return

    is_available = await ollama.check_availability()
    status = Emoji.ACTIVE + " Ishlayapti" if is_available else Emoji.ERROR + " O'chirilgan"

    text = Messages.AI_STATUS.format(
        host=settings.ollama_host,
        model=settings.ollama_default_model,
        status=status,
    )
    await update.effective_message.reply_text(text, parse_mode="HTML")


async def ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """AI menyu callback."""
    if not update.callback_query:
        return
    query = update.callback_query
    await query.answer()

    if query.data == "ai:models":
        models = await ollama.list_models()
        if not models:
            await query.edit_message_text(Messages.AI_NO_MODELS)
            return
        lines = [f"• {m.get('name', 'Noma\'lum')}" for m in models]
        text = Messages.AI_MODEL_LIST.format(models="\n".join(lines))
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")
    elif query.data == "ai:status":
        is_available = await ollama.check_availability()
        status = Emoji.ACTIVE + " Ishlayapti" if is_available else Emoji.ERROR + " O'chirilgan"
        text = Messages.AI_STATUS.format(
            host=settings.ollama_host,
            model=settings.ollama_default_model,
            status=status,
        )
        await query.edit_message_text(text, reply_markup=get_back_keyboard(), parse_mode="HTML")


def register_ai_handlers(application) -> None:
    application.add_handler(CommandHandler("ai", ai_command))
    application.add_handler(CommandHandler("ai_model", ai_model_command))
    application.add_handler(CommandHandler("ai_status", ai_status_command))
    application.add_handler(CallbackQueryHandler(ai_callback, pattern="^ai:"))
