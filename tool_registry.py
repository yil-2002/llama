"""Central registry of "tools" the AI agent can call.

Every entry maps a short tool name to:
  - desc: one-line description shown to the LLM when deciding which tool fits
  - params: {param_name: type_hint_str} - the arguments the tool accepts
  - fn: an async callable(**params) -> str (a short, human-readable result)
  - destructive: if True, the action is never run directly - it always
    goes through the existing confirm_destructive / CONFIRM_REGISTRY flow
    (see bot/utils/decorators.py and bot/handlers/confirm.py) before running.

To add a new capability for the agent, add ONE entry here - nothing else
needs to change in bot/services/agent_service.py or bot/handlers/agent.py.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from bot.services import BackupService, DockerService, SystemService, WireguardService
from bot.utils import bytes_to_human

system_service = SystemService()
docker_service = DockerService()
backup_service = BackupService()
wireguard_service = WireguardService()


ToolFn = Callable[..., Awaitable[str]]


async def _tool_system_status(**_: Any) -> str:
    stats = await system_service.get_stats()
    uptime = await system_service.get_uptime()
    return (
        f"CPU: {stats.cpu_percent:.1f}%\n"
        f"RAM: {stats.ram_percent:.1f}% ({bytes_to_human(stats.ram_used_bytes)}/{bytes_to_human(stats.ram_total_bytes)})\n"
        f"Disk: {stats.disk_percent:.1f}% ({bytes_to_human(stats.disk_used_bytes)}/{bytes_to_human(stats.disk_total_bytes)})\n"
        f"Load: {stats.load_avg_1m:.2f}\n"
        f"Uptime: {uptime}"
    )


async def _tool_top_processes(**_: Any) -> str:
    procs = await system_service.get_top_processes(sort_by="cpu", limit=5)
    lines = [f"{p.get('name', '?')} (PID {p.get('pid', '?')}) - CPU {p.get('cpu_percent', 0):.1f}%" for p in procs]
    return "\n".join(lines) if lines else "Jarayonlar topilmadi."


async def _tool_docker_list(**_: Any) -> str:
    containers = await docker_service.list_containers(all_containers=True)
    if not containers:
        return "Konteynerlar topilmadi."
    lines = [f"{c.get('name', '?')} - {c.get('status', '?')}" for c in containers if "name" in c]
    return "\n".join(lines) if lines else "Konteynerlar topilmadi."


async def _tool_docker_restart(name: str = "", **_: Any) -> str:
    if not name:
        return "Konteyner nomi ko'rsatilmagan."
    result = await docker_service.restart_container(name)
    return f"'{name}' qayta ishga tushirildi." if result.get("success") else f"Xatolik: {result.get('error')}"


async def _tool_docker_stop(name: str = "", **_: Any) -> str:
    if not name:
        return "Konteyner nomi ko'rsatilmagan."
    result = await docker_service.stop_container(name)
    return f"'{name}' to'xtatildi." if result.get("success") else f"Xatolik: {result.get('error')}"


async def _tool_docker_start(name: str = "", **_: Any) -> str:
    if not name:
        return "Konteyner nomi ko'rsatilmagan."
    result = await docker_service.start_container(name)
    return f"'{name}' ishga tushirildi." if result.get("success") else f"Xatolik: {result.get('error')}"


async def _tool_docker_prune(**_: Any) -> str:
    result = await docker_service.prune_images()
    return f"Tozalandi: {result}" if result.get("success", True) else f"Xatolik: {result.get('error')}"


async def _tool_backup_create(name: str = "manual", backup_type: str = "full", **_: Any) -> str:
    result = await backup_service.create_backup(name=name, backup_type=backup_type)
    if result.get("success"):
        return f"Zaxira yaratildi: {result.get('name')} ({result.get('size_human')})"
    return f"Xatolik: {result.get('error')}"


async def _tool_vpn_status(**_: Any) -> str:
    status = await wireguard_service.get_status()
    return str(status)


async def _tool_reboot_server(**_: Any) -> str:
    result = await system_service.reboot()
    return str(result)


async def _tool_shutdown_server(**_: Any) -> str:
    result = await system_service.shutdown()
    return str(result)


TOOLS: Dict[str, Dict[str, Any]] = {
    "system_status": {
        "desc": "Serverning CPU, RAM, disk, load va uptime holatini ko'rsatadi.",
        "params": {},
        "fn": _tool_system_status,
        "destructive": False,
    },
    "top_processes": {
        "desc": "Eng ko'p CPU ishlatayotgan jarayonlarni ko'rsatadi.",
        "params": {},
        "fn": _tool_top_processes,
        "destructive": False,
    },
    "docker_list": {
        "desc": "Barcha Docker konteynerlar va ularning holatini ro'yxatlaydi.",
        "params": {},
        "fn": _tool_docker_list,
        "destructive": False,
    },
    "docker_restart": {
        "desc": "Berilgan nomdagi Docker konteynerni qayta ishga tushiradi.",
        "params": {"name": "str - konteyner nomi"},
        "fn": _tool_docker_restart,
        "destructive": True,
    },
    "docker_stop": {
        "desc": "Berilgan nomdagi Docker konteynerni to'xtatadi.",
        "params": {"name": "str - konteyner nomi"},
        "fn": _tool_docker_stop,
        "destructive": True,
    },
    "docker_start": {
        "desc": "Berilgan nomdagi to'xtagan Docker konteynerni ishga tushiradi.",
        "params": {"name": "str - konteyner nomi"},
        "fn": _tool_docker_start,
        "destructive": False,
    },
    "docker_prune": {
        "desc": "Ishlatilmayotgan Docker image'larni tozalab, joy bo'shatadi.",
        "params": {},
        "fn": _tool_docker_prune,
        "destructive": True,
    },
    "backup_create": {
        "desc": "Yangi zaxira (backup) yaratadi.",
        "params": {"name": "str - zaxira nomi (ixtiyoriy)", "backup_type": "str - full/docker/db/config"},
        "fn": _tool_backup_create,
        "destructive": False,
    },
    "vpn_status": {
        "desc": "WireGuard VPN holati va ulangan peer'larni ko'rsatadi.",
        "params": {},
        "fn": _tool_vpn_status,
        "destructive": False,
    },
    "reboot_server": {
        "desc": "Butun serverni qayta yuklaydi. Juda ehtiyot bo'lish kerak.",
        "params": {},
        "fn": _tool_reboot_server,
        "destructive": True,
    },
    "shutdown_server": {
        "desc": "Butun serverni o'chiradi. Juda ehtiyot bo'lish kerak.",
        "params": {},
        "fn": _tool_shutdown_server,
        "destructive": True,
    },
}
