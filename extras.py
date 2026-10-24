import os
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

# ═══════════════════════════════════════════════════════════════
# 🔧 أدوات مساعدة
# ═══════════════════════════════════════════════════════════════

def _load_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: log.error("فشل حفظ %s: %s", path, e)

# ═══════════════════════════════════════════════════════════════
# ⏰ نظام التذكيرات
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

async def reminder_loop(bot: commands.Bot):
    await bot.wait_until_ready()
    global REMINDERS
    REMINDERS = _load_json(config.REMINDERS_FILE, [])
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
            if due: _save_json(config.REMINDERS_FILE, REMINDERS)
        except Exception as e: log.error("خطأ في التذكيرات: %s", e)
        await asyncio.sleep(30)

# ═══════════════════════════════════════════════════════════════
# 🔒 نظام التوقيف المؤقت
# ═══════════════════════════════════════════════════════════════

TEMP_ACTIONS: list = []

def load_temp_actions():
    global TEMP_ACTIONS
    TEMP_ACTIONS = _load_json(config.TEMP_ACTIONS_FILE, [])

def save_temp_actions():
    _save_json(config.TEMP_ACTIONS_FILE, TEMP_ACTIONS)

async def temp_actions_loop(bot: commands.Bot):
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
# 🎣 مكافحة التصيد (Anti-Phishing)
# ═══════════════════════════════════════════════════════════════

PHISHING_PATTERN = re.compile(r"(https?://)?([a-z0-9\-\.]+\.[a-z]{2,})(/[^\s]*)?", re.IGNORECASE)

def detect_phishing(content: str) -> Optional[str]:
    if not content: return None
    lower = content.lower()
    for domain in config.PHISHING_DOMAINS:
        if domain in lower: return domain
    return None

# ═══════════════════════════════════════════════════════════════
# ⚙️ تحميل الإضافات
# ═══════════════════════════════════════════════════════════════

def load_extras(bot: commands.Bot, shared: dict):
    SHARED.clear()
    SHARED.update(shared)

    # ─── أوامر التذكيرات والتوقيف المؤقت ───
    @bot.tree.command(name="تذكير", description="⏰ ضع تذكيراً بعد مدة")
    @app_commands.describe(duration="مثل: 10m / 2h / 1d", text="نص التذكير")
    async def remind_cmd(interaction: discord.Interaction, duration: str, text: str):
        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message("❌ صيغة خاطئة (مثال: 10m).", ephemeral=True)
            return
        REMINDERS.append({"user_id": interaction.user.id, "text": text, "due": time.time() + seconds})
        _save_json(config.REMINDERS_FILE, REMINDERS)
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
        check = SHARED.get("require_control")
        if check and not await check(interaction): return
        actions = [a for a in TEMP_ACTIONS if a["guild_id"] == interaction.guild.id]
        if not actions:
            await interaction.response.send_message("ℹ️ لا توجد توقيفات مؤقتة.", ephemeral=True)
            return
        lines = [f"🚔 <@{a['user_id']}> — تبقى: **{format_duration(int(a['until'] - time.time()))}**" for a in actions[:20]]
        await interaction.response.send_message(embed=discord.Embed(title="🚔 التوقيفات المؤقتة", description="\n".join(lines), color=discord.Color.orange()), ephemeral=True)

    # ─── حماية من التصيد (تعمل بالخلفية) ───
    async def anti_phishing_handler(message: discord.Message):
        if message.author.bot or not message.guild: return
        is_exempted = SHARED.get("is_exempted")
        if is_exempted and is_exempted(message.author): return
        
        link = detect_phishing(message.content)
        if link:
            try: await message.delete()
            except Exception: pass
            apply_jail = SHARED.get("apply_jail")
            if apply_jail:
                await apply_jail(message.guild, message.author, f"Anti-Phishing: {link}")
            log.warning(f"تم حظر رابط تصيد: {link}")

    bot.add_listener(anti_phishing_handler, "on_message")

    # ─── بدء المهام ───
    async def start_tasks():
        if getattr(bot, "_extras_started", False): return
        bot._extras_started = True
        asyncio.create_task(reminder_loop(bot))
        asyncio.create_task(temp_actions_loop(bot))
        log.info("✅ تم تشغيل مهام extras بنجاح")

    bot.add_listener(start_tasks, "on_ready")
