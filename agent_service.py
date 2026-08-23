"""Natural-language command routing via Ollama (agentic layer, phase 4).

route_message() sends the user's free-text message to the local Ollama
model together with a description of every tool in
bot.services.tool_registry.TOOLS, and asks it to reply with structured
JSON choosing either a tool + params, or a plain conversational reply.

Destructive tools are NEVER executed directly from here - the caller
(bot/handlers/agent.py) is responsible for routing anything with
destructive=True through an explicit confirmation step before calling
execute_tool().
"""
from __future__ import annotations

import json
from typing import Any

from loguru import logger

from bot.config import settings
from bot.services.ollama_service import OllamaService
from bot.services.tool_registry import TOOLS

ollama_service = OllamaService()

SYSTEM_PROMPT_TEMPLATE = (
    "Sen VPS serverni boshqaruvchi Telegram botning yordamchi miyasisan. "
    "Foydalanuvchi xabariga qarab, quyidagi vositalardan eng mosini tanla. "
    "Agar hech biri mos kelmasa yoki xabar shunchaki savol/salomlashish bo'lsa, "
    "tool ni null qilib, reply maydoniga qisqa javob yoz.\n\n"
    "Mavjud vositalar:\n{tools_desc}\n\n"
    "Javobni FAQAT quyidagi JSON formatda qaytar, boshqa hech qanday matn yozma:\n"
    '{{"tool": "<vosita_nomi yoki null>", "params": {{...}}, "reply": "<tool null bo\'lsa qisqa javob>"}}'
)


def _build_tools_description() -> str:
    lines = []
    for name, meta in TOOLS.items():
        params_desc = ", ".join(f"{k} ({v})" for k, v in meta["params"].items()) or "parametrsiz"
        danger = " [DESTRUKTIV]" if meta.get("destructive") else ""
        lines.append(f"- {name}: {meta['desc']} [{params_desc}]{danger}")
    return "\n".join(lines)


async def route_message(text: str) -> dict[str, Any]:
    """Decide which tool (if any) matches a free-text message.

    Returns {"tool": str|None, "params": dict, "reply": str}.
    "tool" is None when nothing matched or the response failed to parse -
    in that case "reply" holds a message to show the user.
    """
    system = SYSTEM_PROMPT_TEMPLATE.format(tools_desc=_build_tools_description())
    model = settings.agent_model or settings.ollama_default_model
    result = await ollama_service.generate(prompt=text, system=system, json_mode=True, model=model)

    if not result.get("success"):
        return {
            "tool": None,
            "params": {},
            "reply": f"AI xizmati javob bermadi: {result.get('error', 'noma\'lum xato')}",
        }

    raw = (result.get("response") or "").strip()
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Agent JSON parse xatosi, xom javob: {raw[:200]!r}")
        return {"tool": None, "params": {}, "reply": raw or "Tushunmadim, qaytadan urinib ko'ring."}

    if not isinstance(parsed, dict):
        return {"tool": None, "params": {}, "reply": "Tushunmadim, qaytadan urinib ko'ring."}

    tool_name = parsed.get("tool")
    if tool_name and tool_name not in TOOLS:
        logger.warning(f"Agent noma'lum vosita tanladi: {tool_name!r}")
        tool_name = None

    params = parsed.get("params")
    if not isinstance(params, dict):
        params = {}

    return {
        "tool": tool_name,
        "params": params,
        "reply": parsed.get("reply") or "",
    }


async def execute_tool(tool_name: str, params: dict[str, Any]) -> str:
    """Run a tool by name. Caller must have already handled confirmation
    for destructive tools - this function does not check that flag."""
    tool = TOOLS.get(tool_name)
    if not tool:
        return "Noma'lum vosita."
    try:
        return await tool["fn"](**params)
    except TypeError as e:
        logger.warning(f"Vosita '{tool_name}' uchun noto'g'ri parametrlar: {params} ({e})")
        return "Berilgan ma'lumotlar yetarli emas yoki noto'g'ri."
    except Exception as e:
        logger.error(f"Vosita bajarishda xatolik ({tool_name}): {e}")
        return f"Xatolik yuz berdi: {e}"
