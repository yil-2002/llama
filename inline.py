"""Inline keyboard factory functions."""
from __future__ import annotations

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constants import ButtonText, Emoji


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Asosiy menyu klaviaturasi."""
    keyboard = []
    for row in ButtonText.MAIN_MENU:
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"menu:{text.split()[1]}")
            for text in row
        ])
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard(callback_data: str = "menu:main") -> InlineKeyboardMarkup:
    """Orqaga tugmasi bilan klaviatura."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.BACK, callback_data=callback_data)],
        [InlineKeyboardButton(ButtonText.MAIN_MENU_BTN, callback_data="menu:main")],
    ])


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    prefix: str,
    extra_buttons: Optional[list[list[InlineKeyboardButton]]] = None,
) -> InlineKeyboardMarkup:
    """Sahifalash klaviaturasi."""
    keyboard = []
    nav_row = []
    if current_page > 1:
        nav_row.append(InlineKeyboardButton(ButtonText.PREV, callback_data=f"{prefix}:page:{current_page - 1}"))
    nav_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton(ButtonText.NEXT, callback_data=f"{prefix}:page:{current_page + 1}"))
    if nav_row:
        keyboard.append(nav_row)
    if extra_buttons:
        keyboard.extend(extra_buttons)
    keyboard.append([InlineKeyboardButton(ButtonText.BACK, callback_data=f"{prefix}:back")])
    keyboard.append([InlineKeyboardButton(ButtonText.MAIN_MENU_BTN, callback_data="menu:main")])
    return InlineKeyboardMarkup(keyboard)


def get_docker_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.START, callback_data="docker:running")],
        [InlineKeyboardButton(ButtonText.STOP, callback_data="docker:stopped")],
        [InlineKeyboardButton(ButtonText.STATS, callback_data="docker:stats")],
        [InlineKeyboardButton(ButtonText.LOGS, callback_data="docker:compose")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_monitoring_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.STATS, callback_data="monitor:status")],
        [InlineKeyboardButton("Top Protsesslar", callback_data="monitor:top")],
        [InlineKeyboardButton(ButtonText.NETWORK, callback_data="monitor:net")],
        [InlineKeyboardButton("Tarix", callback_data="monitor:history")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_backup_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.FULL_BACKUP, callback_data="backup:type:full")],
        [InlineKeyboardButton(ButtonText.DOCKER_BACKUP, callback_data="backup:type:docker")],
        [InlineKeyboardButton(ButtonText.DB_BACKUP, callback_data="backup:type:db")],
        [InlineKeyboardButton(ButtonText.CONFIG_BACKUP, callback_data="backup:type:config")],
        [InlineKeyboardButton(ButtonText.CUSTOM_BACKUP, callback_data="backup:type:custom")],
        [InlineKeyboardButton(ButtonText.SCHEDULE, callback_data="backup:schedule")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_system_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.SERVICES, callback_data="system:services")],
        [InlineKeyboardButton(ButtonText.UPDATE, callback_data="system:update")],
        [InlineKeyboardButton(ButtonText.FIREWALL, callback_data="system:ufw")],
        [InlineKeyboardButton(ButtonText.CRON, callback_data="system:cron")],
        [InlineKeyboardButton(ButtonText.RESTART, callback_data="system:reboot")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_nginx_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.SITES, callback_data="nginx:sites")],
        [InlineKeyboardButton(ButtonText.SSL, callback_data="nginx:ssl")],
        [InlineKeyboardButton(ButtonText.CERT, callback_data="nginx:renew")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_db_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.PGSQL, callback_data="db:pgsql")],
        [InlineKeyboardButton(ButtonText.MYSQL, callback_data="db:mysql")],
        [InlineKeyboardButton(ButtonText.REDIS, callback_data="db:redis")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_logs_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.BOT_LOGS, callback_data="logs:bot")],
        [InlineKeyboardButton(ButtonText.SYSTEM_LOGS, callback_data="logs:system")],
        [InlineKeyboardButton(ButtonText.SERVICE_LOGS, callback_data="logs:service")],
        [InlineKeyboardButton(ButtonText.NGINX_LOGS, callback_data="logs:nginx")],
        [InlineKeyboardButton(ButtonText.DOCKER_LOGS, callback_data="logs:docker")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_ai_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Modelni almashtirish", callback_data="ai:models")],
        [InlineKeyboardButton("Holat", callback_data="ai:status")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_vpn_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.STATS, callback_data="vpn:status")],
        [InlineKeyboardButton(ButtonText.ADD, callback_data="vpn:add")],
        [InlineKeyboardButton(ButtonText.REMOVE, callback_data="vpn:remove")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_media_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.LIBRARIES, callback_data="media:libs")],
        [InlineKeyboardButton(ButtonText.RECENT, callback_data="media:recent")],
        [InlineKeyboardButton(ButtonText.SCAN, callback_data="media:scan")],
        [InlineKeyboardButton(ButtonText.USERS, callback_data="media:users")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])


def get_git_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(ButtonText.REPOS, callback_data="git:repos")],
        [InlineKeyboardButton(ButtonText.CREATE_REPO, callback_data="git:create_repo")],
        [InlineKeyboardButton(ButtonText.USERS, callback_data="git:users")],
        [InlineKeyboardButton(ButtonText.BACK, callback_data="menu:main")],
    ])
