import os

BOT_OWNER_ID = 813236200142929950
TOKEN = os.getenv("DISCORD_TOKEN")

# 📁 المسارات
DATA_DIR = "data"
BACKUPS_DIR = "data/backups"
ICONS_DIR = "data/backups/icons"
BANNERS_DIR = "data/backups/banners"
LOGS_DIR = "logs"
CARDS_DIR = "data/welcome_cards"

WARNINGS_FILE = "data/warnings.json"
STATE_FILE = "data/state.json"
ANTINUKE_FILE = "data/antinuke.json"
GUILD_CACHE_FILE = "data/guild_cache.json"
BACKUP_FILE = "data/backup_meta.json"
BOT_LOG_FILE = "logs/bot.log"

# 🎭 الرتب
CITIZEN_ROLE = {"id": None, "names": ["🇸🇦〢سعودي", "سعودي", "مواطن"]}
ROLE_JAIL = {"id": None, "names": ["🚔〢متوقف", "متوقف", "محجور"]}
# تم تعديل وزير الداخلية إلى رئيس الوزراء
ROLE_PRIME_MINISTER = {"id": None, "names": ["👑〢رئيس-الوزراء", "رئيس-الوزراء", "رئيس الوزراء", "وزير-الداخلية", "وزير الداخلية"]}
ROLE_TICKET = {"id": None, "names": ["مسؤول-التذاكر", "Support", "الدعم"]}
ROLE_APPLY = {"id": None, "names": ["مسؤول-التقديم", "Applications", "تقديم"]}

# 📢 الرومات
CH_ADMIN_REVIEW = {"id": 1548492573813776435, "names": ["admin-review"]}
CH_JAIL = {"id": 1532133484129161347, "names": ["quarantine-zone", "التوقيف"]}
CH_LOG_MANUAL = {"id": 1560281673046818926, "names": ["لوق_العقوبات_اليدوية"]}
CH_LOG_AUTO = {"id": 1548492573813776435, "names": ["admin-review"]}
CH_LOG_CHANGES = {"id": 1510246552256385124, "names": ["لوق_التعديلات"]}
CH_LOG_TICKETS = {"id": 1548492573813776435, "names": ["admin-review"]}
CH_LOG_LEAVE = {"id": 1510246429908537424, "names": ["لوق_الخروج"]}
CH_WELCOME = {"id": 1549343919203033118, "names": ["الترحيب"]}
CH_ANNOUNCE = {"id": 1549470907834044436, "names": ["الإعلانات"]}
CH_TICKET_PANEL = {"id": 1548500331032354896, "names": ["البرقيات"]}
CH_APPLY_PANEL = {"id": 1548500336543535224, "names": ["التقديم"]}
CH_TICKET_CATEGORY = {"id": None, "names": ["البرقيات", "Tickets"]}

# 🛡️ Anti-Nuke
ANTI_NUKE_ENABLED = True
ANTI_NUKE_PUNISHMENT = "jail"
ANTI_NUKE_DECAY_AFTER = 60
ANTI_NUKE_THRESHOLDS = {
    "channel_delete": {"count": 3, "seconds": 10},
    "channel_create": {"count": 5, "seconds": 10},
    "channel_update": {"count": 5, "seconds": 10},
    "role_delete":    {"count": 3, "seconds": 10},
    "role_create":    {"count": 5, "seconds": 10},
    "role_update":    {"count": 5, "seconds": 10},
    "ban":            {"count": 5, "seconds": 10},
    "kick":           {"count": 5, "seconds": 10},
    "bot_add":        {"count": 2, "seconds": 30},
    "webhook_create": {"count": 2, "seconds": 30},
}
GRADUATED_NUKE_PUNISHMENT = True

BACKUP_ENABLED = True
BACKUP_MAX_ICONS = 5
BACKUP_MAX_BANNERS = 3

RATE_LIMITS = {
    "أمر_توقيف": {"max": 10, "window": 60},
    "إنذار_رسمي": {"max": 15, "window": 60},
    "تنظيف": {"max": 5, "window": 60},
    "بيان_رسمي": {"max": 3, "window": 60},
    "تذكير": {"max": 10, "window": 300},
}

AUTOMOD_ENABLED = True
AUTOMOD_SETTINGS = {
    "max_mentions": 6, "mentions_action": "warn",
    "max_duplicates": 3, "duplicate_window": 5, "duplicate_action": "warn",
    "max_zalgo": 15, "zalgo_action": "delete_only",
    "max_symbols_percent": 0.5, "symbols_action": "delete_only",
}

ROLE_NOTIFY_ENABLED = True
ROLE_NOTIFY_IGNORE = ["🚔〢متوقف", "متوقف"]

RULES_TEXT = """📜 قوانين وعقوبات السيرفر:\n\n1. السب والشتم: توقيف فوري.\n2. الروابط: إنذار + تايم آوت.\n3. السبام: إنذار + تايم آوت.\n4. منشن الجميع: إنذار + تايم آوت.\n5. الاحترام المتبادل.\n\n⚠️ عند 3 إنذارات يتم التوقيف!"""

BAD_WORDS = ["كلب", "حمار", "قحبة", "شرموط", "fuck", "shit", "bitch"]import os
import re
import json
import time
import asyncio
import logging
import datetime
from typing import Optional
import discord
from discord.ext import commands
from discord import app_commands

import config

log = logging.getLogger("extras")
SHARED: dict = {}

def _load_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def _save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: log.error("فشل حفظ %s: %s", path, e)

# ═══════════════════════════════════════════════════════════════
# ⏰ التذكيرات
# ═══════════════════════════════════════════════════════════════
REMINDERS: list = []

def parse_duration(text: str) -> Optional[int]:
    if not text: return None
    pattern = re.compile(r"(\d+)\s*(d|h|m|s|يوم|ساعة|دقيقة|ثانية)", re.IGNORECASE)
    units = {"s": 1, "ثانية": 1, "m": 60, "دقيقة": 60, "h": 3600, "ساعة": 3600, "d": 86400, "يوم": 86400}
    total = 0
    for match in pattern.finditer(text):
        num = int(match.group(1))
        unit = match.group(2).lower()
        if unit in units: total += num * units[unit]
    return total if total > 0 else None

def format_duration(seconds: int) -> str:
    if seconds < 60: return f"{seconds} ثانية"
    if seconds < 3600: return f"{seconds // 60} دقيقة"
    if seconds < 86400: return f"{seconds // 3600} ساعة"
    return f"{seconds // 86400} يوم"

async def reminder_loop(bot):
    global REMINDERS
    await bot.wait_until_ready()
    REMINDERS = _load_json(config.REMINDERS_FILE if hasattr(config, 'REMINDERS_FILE') else "data/reminders.json", [])
    while True:
        try:
            now = time.time()
            due = [r for r in REMINDERS if r["due"] <= now]
            for r in due:
                try:
                    user = await bot.fetch_user(r["user_id"])
                    if user: await user.send(f"⏰ **تذكير:**\n{r['text']}")
                except Exception: pass
                REMINDERS.remove(r)
            if due: _save_json("data/reminders.json", REMINDERS)
        except Exception as e: log.error("خطأ في التذكيرات: %s", e)
        await asyncio.sleep(30)

# ═══════════════════════════════════════════════════════════════
# 🔒 التوقيف المؤقت
# ═══════════════════════════════════════════════════════════════
TEMP_ACTIONS: list = []

def load_temp_actions():
    global TEMP_ACTIONS
    TEMP_ACTIONS = _load_json("data/temp_actions.json", [])

def save_temp_actions():
    _save_json("data/temp_actions.json", TEMP_ACTIONS)

async def temp_actions_loop(bot):
    global TEMP_ACTIONS
    await bot.wait_until_ready()
    load_temp_actions()
    while True:
        try:
            now = time.time()
            due = [a for a in TEMP_ACTIONS if a["until"] <= now]
            for action in due:
                guild = bot.get_guild(action["guild_id"])
                if guild:
                    member = guild.get_member(action["user_id"])
                    if member and action["type"] == "jail":
                        remove_jail = SHARED.get("remove_jail")
                        if remove_jail: await remove_jail(guild, member)
                if action in TEMP_ACTIONS: TEMP_ACTIONS.remove(action)
            if due: save_temp_actions()
        except Exception as e: log.error("خطأ في العقوبات المؤقتة: %s", e)
        await asyncio.sleep(30)

# ═══════════════════════════════════════════════════════════════
# 🎣 مكافحة التصيد
# ═══════════════════════════════════════════════════════════════
PHISHING_DOMAINS = ["discord-nitro.com", "discordnitro.com", "discord-gift.com", "steamcommunlty.com", "free-nitro.com", "claim-nitro.com", "dlscord.com", "discordgift.site", "discordgift.xyz"]

def detect_phishing(content: str) -> Optional[str]:
    if not content: return None
    lower = content.lower()
    for domain in PHISHING_DOMAINS:
        if domain in lower: return domain
    return None

# ═══════════════════════════════════════════════════════════════
# ⚙️ التحميل
# ═══════════════════════════════════════════════════════════════
def load_extras(bot: commands.Bot, shared: dict):
    SHARED.clear()
    SHARED.update(shared)

    @bot.tree.command(name="تذكير", description="⏰ ضع تذكيراً بعد مدة")
    @app_commands.describe(duration="مثل: 10m / 2h / 1d", text="نص التذكير")
    async def remind_cmd(interaction: discord.Interaction, duration: str, text: str):
        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message("❌ صيغة خاطئة (مثال: 10m).", ephemeral=True)
            return
        REMINDERS.append({"user_id": interaction.user.id, "text": text, "due": time.time() + seconds})
        _save_json("data/reminders.json", REMINDERS)
        await interaction.response.send_message(f"✅ تم وضع تذكير بعد {format_duration(seconds)}.", ephemeral=True)

    @bot.tree.command(name="توقيف_مؤقت", description="🚔 توقيف مؤقت مع فك تلقائي")
    @app_commands.describe(member="العضو", duration="مثل: 1h / 1d", reason="السبب")
    async def tempjail_cmd(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "لم يحدد"):
        check = SHARED.get("require_control")
        if check and not await check(interaction): return
        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message("❌ صيغة خاطئة.", ephemeral=True)
            return
        apply_jail = SHARED.get("apply_jail")
        if not apply_jail:
            await interaction.response.send_message("❌ خطأ داخلي.", ephemeral=True)
            return
        ok, msg = await apply_jail(interaction.guild, member, reason, duration_text=format_duration(seconds), issued_by=interaction.user)
        if ok:
            TEMP_ACTIONS.append({"guild_id": interaction.guild.id, "user_id": member.id, "type": "jail", "until": time.time() + seconds, "reason": reason})
            save_temp_actions()
            await interaction.response.send_message(msg + f"\n⏱️ المدة: {format_duration(seconds)}", ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    @bot.tree.command(name="قائمة_التوقيفات", description="📋 عرض التوقيفات المؤقتة")
    async def temp_list_cmd(interaction: discord.Interaction):
        actions = [a for a in TEMP_ACTIONS if a["guild_id"] == interaction.guild.id]
        if not actions:
            await interaction.response.send_message("ℹ️ لا توجد توقيفات مؤقتة.", ephemeral=True)
            return
        lines = [f"🚔 <@{a['user_id']}> — تبقى: **{format_duration(int(a['until'] - time.time()))}**" for a in actions[:20]]
        await interaction.response.send_message(embed=discord.Embed(title="🚔 التوقيفات المؤقتة", description="\n".join(lines), color=discord.Color.orange()), ephemeral=True)

    async def anti_phishing_handler(message: discord.Message):
        if message.author.bot or not message.guild: return
        is_exempted = SHARED.get("is_exempted")
        if is_exempted and is_exempted(message.author): return
        link = detect_phishing(message.content)
        if link:
            try: await message.delete()
            except Exception: pass
            apply_jail = SHARED.get("apply_jail")
            if apply_jail: await apply_jail(message.guild, message.author, f"Anti-Phishing: {link}")

    bot.add_listener(anti_phishing_handler, "on_message")

    async def start_tasks():
        if getattr(bot, "_extras_started", False): return
        bot._extras_started = True
        asyncio.create_task(reminder_loop(bot))
        asyncio.create_task(temp_actions_loop(bot))

    bot.add_listener(start_tasks, "on_ready")
