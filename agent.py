"""Free-text natural language command routing (agentic layer, phase 4).

Any plain-text message that is NOT a command reaches this handler after
the global auth gate (group=-1) has already confirmed the session is
valid - see bot/middlewares/auth.py. The message is handed to
bot.services.agent_service.route_message(), which asks Ollama to pick a
matching tool from bot.services.tool_registry.TOOLS.

Destructive tools (docker_restart, reboot_server, etc.) always require an
explicit inline "Ha/Yo'q" confirmation before running - the pending call
(tool name + params) is stashed in context.user_data until the user taps
a button, exactly mirroring the confirm_destructive() flow used for
static commands (bot/handlers/confirm.py), but with dynamic params.
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from bot.constants import ButtonText, Messages
from bot.services import agent_service
from bot.services.tool_registry import TOOLS
from bot.utils import log_execution


def _build_agent_confirm_keyboard(tool_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(ButtonText.CONFIRM_GO, callback_data=f"agent_confirm:go:{tool_name}"),
                InlineKeyboardButton(ButtonText.CONFIRM_CANCEL, callback_data=f"agent_confirm:cancel:{tool_name}"),
            ]
        ]
    )


@log_execution("agent")
async def agent_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_message or not update.effective_message.text:
        return

    text = update.effective_message.text
    await update.effective_message.reply_text(Messages.AGENT_THINKING)

    result = await agent_service.route_message(text)
    tool_name = result.get("tool")

    if not tool_name:
        await update.effective_message.reply_text(result.get("reply") or Messages.AGENT_NO_MATCH)
        return

    tool = TOOLS[tool_name]
    params = result.get("params") or {}

    if tool["destructive"]:
        if context.user_data is not None:
            context.user_data["pending_tool_call"] = {"tool": tool_name, "params": params}
        await update.effective_message.reply_text(
            Messages.AGENT_CONFIRM.format(tool=tool_name, params=params),
            reply_markup=_build_agent_confirm_keyboard(tool_name),
            parse_mode="HTML",
        )
        return

    output = await agent_service.execute_tool(tool_name, params)
    await update.effective_message.reply_text(
        Messages.AGENT_RESULT.format(tool=tool_name, output=output), parse_mode="HTML"
    )


async def agent_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the Ha/Yo'q buttons shown for a destructive agent-picked tool."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) < 3:
        return
    _, verdict, tool_name = parts

    pending = (context.user_data or {}).get("pending_tool_call")
    if context.user_data is not None:
        context.user_data["pending_tool_call"] = None

    if verdict == "cancel" or not pending or pending.get("tool") != tool_name:
        await query.edit_message_text(Messages.OPERATION_CANCELLED)
        return

    await query.edit_message_text(Messages.PROCESSING)
    output = await agent_service.execute_tool(tool_name, pending.get("params") or {})
    await query.edit_message_text(
        Messages.AGENT_RESULT.format(tool=tool_name, output=output), parse_mode="HTML"
    )


def register_agent_handlers(application) -> None:
    # Plain text only (filters.COMMAND is excluded) - never shadows any
    # CommandHandler, and never sees updates the global auth gate stopped.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, agent_message_handler))
    application.add_handler(CallbackQueryHandler(agent_confirm_callback, pattern="^agent_confirm:"))
