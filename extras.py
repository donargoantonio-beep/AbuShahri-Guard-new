# ═══════════════════════════════════════════════════════════════
# 📦 القسم 1: الاستيراد والمكتبات
# ═══════════════════════════════════════════════════════════════
import os
import re
import io
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


# ═══════════════════════════════════════════════════════════════
# 🔧 القسم 2: الأدوات المشتركة (SHARED + JSON)
# ═══════════════════════════════════════════════════════════════

SHARED: dict = {}


def _load_json(path, default):
    """قراءة ملف JSON بأمان"""
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    """كتابة ملف JSON بأمان"""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("فشل حفظ %s: %s", path, e)


# ═══════════════════════════════════════════════════════════════
# ⏰ القسم 3: نظام التذكيرات
# ═══════════════════════════════════════════════════════════════

REMINDERS: list = []


def parse_duration(text: str) -> Optional[int]:
    """يحوّل نص مثل 10m / 2h / 1d / 30s إلى ثواني"""
    if not text:
        return None

    pattern = re.compile(r"(\d+)\s*(d|h|m|s|يوم|ساعة|دقيقة|ثانية)", re.IGNORECASE)
    units = {
        "s": 1, "ثانية": 1,
        "m": 60, "دقيقة": 60,
        "h": 3600, "ساعة": 3600,
        "d": 86400, "يوم": 86400,
    }

    total = 0
    found = False
    for match in pattern.finditer(text):
        num = int(match.group(1))
        unit = match.group(2).lower()
        if unit in units:
            total += num * units[unit]
            found = True
    return total if found and total > 0 else None


def format_duration(seconds: int) -> str:
    """يحول الثواني إلى نص عربي مختصر"""
    if seconds < 60:
        return str(seconds) + " ثانية"
    if seconds < 3600:
        return str(seconds // 60) + " دقيقة"
    if seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return str(h) + " ساعة" + (" و " + str(m) + " دقيقة" if m else "")
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    return str(d) + " يوم" + (" و " + str(h) + " ساعة" if h else "")


def load_reminders():
    """تحميل التذكيرات من JSON (احتياطي)"""
    global REMINDERS
    REMINDERS = _load_json(config.REMINDERS_FILE, [])


async def save_reminders():
    """حفظ التذكيرات (MongoDB أو JSON)"""
    if config.MONGO_ENABLED:
        try:
            from main import mongo_save
            await mongo_save("reminders", {"data": REMINDERS})
            return
        except Exception as e:
            log.warning("فشل حفظ التذكيرات في MongoDB: %s", e)
    _save_json(config.REMINDERS_FILE, REMINDERS)


async def sync_reminders_from_mongo():
    """يسحب التذكيرات من MongoDB"""
    global REMINDERS
    if not config.MONGO_ENABLED:
        return
    try:
        from main import mongo_read
        data = await mongo_read("reminders", {"data": []})
        REMINDERS = data.get("data", [])
        log.info("تم تحميل %d تذكير من MongoDB", len(REMINDERS))
    except Exception as e:
        log.warning("فشل تحميل التذكيرات من MongoDB: %s", e)


async def reminder_loop(bot: commands.Bot):
    """حلقة تتحقق كل 30 ثانية من التذكيرات المستحقة"""
    await bot.wait_until_ready()
    log.info("حلقة التذكيرات بدأت")

    while True:
        try:
            now = time.time()
            due = [r for r in REMINDERS if r["due"] <= now]

            for r in due:
                try:
                    user = await bot.fetch_user(r["user_id"])
                    if user:
                        embed = discord.Embed(
                            title="تذكير",
                            description=r["text"],
                            color=discord.Color.blurple(),
                            timestamp=discord.utils.utcnow(),
                        )
                        if r.get("channel_id"):
                            ch = bot.get_channel(r["channel_id"])
                            if ch:
                                embed.add_field(name="الروم", value=ch.mention, inline=False)
                        if r.get("original_link"):
                            embed.add_field(name="الرابط", value=r["original_link"], inline=False)

                        await user.send(embed=embed)
                except Exception as e:
                    log.warning("فشل إرسال تذكير: %s", e)

                if r in REMINDERS:
                    REMINDERS.remove(r)

            if due:
                await save_reminders()

        except Exception as e:
            log.exception("خطأ في reminder_loop: %s", e)

        await asyncio.sleep(30)


# ═══════════════════════════════════════════════════════════════
# 🔒 القسم 4: نظام الحجر المؤقت
# ═══════════════════════════════════════════════════════════════

TEMP_ACTIONS: list = []


def load_temp_actions():
    """تحميل العقوبات المؤقتة من JSON (احتياطي)"""
    global TEMP_ACTIONS
    TEMP_ACTIONS = _load_json(config.TEMP_ACTIONS_FILE, [])


async def save_temp_actions():
    """حفظ العقوبات المؤقتة (MongoDB أو JSON)"""
    if config.MONGO_ENABLED:
        try:
            from main import mongo_save
            await mongo_save("temp_actions", {"data": TEMP_ACTIONS})
            return
        except Exception as e:
            log.warning("فشل حفظ العقوبات في MongoDB: %s", e)
    _save_json(config.TEMP_ACTIONS_FILE, TEMP_ACTIONS)


async def sync_temp_actions_from_mongo():
    """يسحب العقوبات المؤقتة من MongoDB"""
    global TEMP_ACTIONS
    if not config.MONGO_ENABLED:
        return
    try:
        from main import mongo_read
        data = await mongo_read("temp_actions", {"data": []})
        TEMP_ACTIONS = data.get("data", [])
        log.info("تم تحميل %d عقوبة مؤقتة من MongoDB", len(TEMP_ACTIONS))
    except Exception as e:
        log.warning("فشل تحميل العقوبات من MongoDB: %s", e)


async def temp_actions_loop(bot: commands.Bot):
    """حلقة تتحقق كل 30 ثانية من العقوبات المنتهية"""
    await bot.wait_until_ready()
    log.info("حلقة العقوبات المؤقتة بدأت")

    while True:
        try:
            now = time.time()
            due = [a for a in TEMP_ACTIONS if a["until"] <= now]

            if due:
                log.info("عقوبات منتهية: %d", len(due))

            for action in due:
                try:
                    guild = bot.get_guild(action["guild_id"])
                    if not guild:
                        if action in TEMP_ACTIONS:
                            TEMP_ACTIONS.remove(action)
                        continue

                    user_id = action["user_id"]
                    kind = action["type"]
                    member = guild.get_member(user_id)

                    if kind == "jail":
                        if member is None:
                            log.warning("العضو %s ليس في السيرفر", user_id)
                        else:
                            remove_jail = SHARED.get("remove_jail")
                            if remove_jail:
                                ok, msg = await remove_jail(guild, member)
                                log.info("فك حجر %s: %s", member, msg)

                    try:
                        get_ch = SHARED.get("get_ch_admin_review")
                        if get_ch:
                            ch = get_ch(guild)
                            if ch:
                                embed = discord.Embed(
                                    title="انتهت مدة الحجر المؤقت",
                                    color=discord.Color.green(),
                                    timestamp=discord.utils.utcnow(),
                                )
                                embed.add_field(
                                    name="العضو",
                                    value="<@" + str(user_id) + "> (" + str(user_id) + ")",
                                    inline=False,
                                )
                                if action.get("reason"):
                                    embed.add_field(
                                        name="السبب الأصلي",
                                        value=action["reason"],
                                        inline=False,
                                    )
                                await ch.send(embed=embed)
                    except Exception as e:
                        log.warning("فشل إرسال إشعار: %s", e)

                except Exception as e:
                    log.exception("فشل إنهاء عقوبة: %s", e)

                if action in TEMP_ACTIONS:
                    TEMP_ACTIONS.remove(action)

            if due:
                await save_temp_actions()
                log.info("تم إنهاء %d عقوبة مؤقتة", len(due))

        except Exception as e:
            log.exception("خطأ في temp_actions_loop: %s", e)

        await asyncio.sleep(30)


# ═══════════════════════════════════════════════════════════════
# 🎣 القسم 5: Anti-Phishing
# ═══════════════════════════════════════════════════════════════

PHISHING_PATTERN = re.compile(
    r"(https?://)?([a-z0-9\-\.]+\.[a-z]{2,})(/[^\s]*)?",
    re.IGNORECASE,
)


def detect_phishing(content: str) -> Optional[str]:
    """يفحص النص ويعيد النطاق المشبوه أو None"""
    if not content:
        return None

    lower = content.lower()

    # 1. فحص النطاقات المعروفة
    for domain in config.PHISHING_DOMAINS:
        if domain in lower:
            return domain

    # 2. كلمات مفتاحية + رابط
    has_url = bool(PHISHING_PATTERN.search(content))
    if has_url:
        for kw in config.PHISHING_KEYWORDS:
            if kw.lower() in lower:
                return "keyword: " + kw + " + رابط"

    # 3. كشف التشابه بالنطاقات الرسمية
    for match in PHISHING_PATTERN.finditer(content):
        domain = match.group(2).lower()
        suspicious_parts = [
            "discord", "dlscord", "discrod",
            "steam", "stearn",
            "twitch", "nitro",
            "free-gift", "gift-claim",
        ]
        for part in suspicious_parts:
            if part in domain and domain not in (
                "discord.com", "discord.gg",
                "discordapp.com",
                "store.steampowered.com",
                "steamcommunity.com",
                "twitch.tv",
            ):
                if not any(official in domain for official in [
                    "discord.com", "discord.gg", "discordapp.com",
                    "steampowered.com", "steamcommunity.com",
                    "twitch.tv",
                ]):
                    return domain

    return None


# ═══════════════════════════════════════════════════════════════
# 🛡️ القسم 6: Auto-Mod
# ═══════════════════════════════════════════════════════════════

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002700-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U00002600-\U000026FF"
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)

ZALGO_RE = re.compile(
    r"[\u0300-\u036f\u0489\u1ab0-\u1aff"
    r"\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]"
)


def count_emojis(text: str) -> int:
    """يعد الإيموجي (بما فيها المخصص)"""
    count = 0
    for match in EMOJI_PATTERN.finditer(text):
        count += len(match.group(0))
    count += len(re.findall(r"<a?:\w+:\d+>", text))
    return count


def caps_percent(text: str) -> float:
    """نسبة الحروف الكبيرة"""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters)


def symbol_percent(text: str) -> float:
    """نسبة الرموز"""
    if not text:
        return 0.0
    symbols = sum(1 for c in text if not c.isalnum() and not c.isspace())
    return symbols / len(text)


def count_zalgo(text: str) -> int:
    """يعد الرموز المشوهة"""
    return len(ZALGO_RE.findall(text))


def automod_check(message) -> Optional[dict]:
    """يفحص الرسالة ويرجع مخالفة أو None"""
    if not config.AUTOMOD_ENABLED:
        return None

    s = config.AUTOMOD_SETTINGS
    content = message.content or ""

    if count_emojis(content) > s["max_emojis"]:
        return {
            "reason": "spam_emoji",
            "action": s["emoji_action"],
            "detail": str(count_emojis(content)) + " إيموجي",
        }

    if len(content) >= s["caps_min_length"] and caps_percent(content) > s["max_caps_percent"]:
        return {
            "reason": "spam_caps",
            "action": s["caps_action"],
            "detail": str(int(caps_percent(content) * 100)) + "% حروف كبيرة",
        }

    if len(message.mentions) > s["max_mentions"]:
        return {
            "reason": "spam_mentions",
            "action": s["mentions_action"],
            "detail": str(len(message.mentions)) + " منشن",
        }

    if count_zalgo(content) > s["max_zalgo"]:
        return {
            "reason": "zalgo",
            "action": s["zalgo_action"],
            "detail": str(count_zalgo(content)) + " رمز مشوه",
        }

    if len(content) >= 10 and symbol_percent(content) > s["max_symbols_percent"]:
        return {
            "reason": "spam_symbols",
            "action": s["symbols_action"],
            "detail": str(int(symbol_percent(content) * 100)) + "% رموز",
        }

    return None


# ═══════════════════════════════════════════════════════════════
# 👋 القسم 7: Welcome Card
# ═══════════════════════════════════════════════════════════════

def _wrap_text(text: str, max_chars: int = 20) -> str:
    """يقص النص الطويل"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "..."


async def make_welcome_card(member: discord.Member) -> Optional[io.BytesIO]:
    """ينشئ صورة ترحيب بالأفاتار والاسم"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log.warning("Pillow غير مثبتة -- Welcome Card معطل")
        return None

    try:
        width, height = config.WELCOME_CARD_SIZE
        bg_color = config.WELCOME_CARD_BG_COLOR
        accent = config.WELCOME_CARD_ACCENT

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        circle_x = 150
        circle_y = height // 2
        circle_r = 100

        draw.ellipse(
            [
                circle_x - circle_r - 5, circle_y - circle_r - 5,
                circle_x + circle_r + 5, circle_y + circle_r + 5,
            ],
            fill=accent,
        )

        avatar_bytes = await member.display_avatar.replace(
            size=256, format="png"
        ).read()

        avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar_img = avatar_img.resize((circle_r * 2, circle_r * 2), Image.LANCZOS)

        mask = Image.new("L", (circle_r * 2, circle_r * 2), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, circle_r * 2, circle_r * 2], fill=255)

        img.paste(avatar_img, (circle_x - circle_r, circle_y - circle_r), mask)

        font_big = None
        font_small = None

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    font_big = ImageFont.truetype(path, 56)
                    font_small = ImageFont.truetype(path, 24)
                    break
                except Exception:
                    continue

        if font_big is None:
            font_big = ImageFont.load_default()
            font_small = font_big

        text_x = 320
        name_text = _wrap_text(member.name, 20)

        draw.text(
            (text_x, height // 2 - 60),
            config.WELCOME_CARD_TITLE,
            fill=accent,
            font=font_small,
        )
        draw.text(
            (text_x, height // 2 - 25),
            name_text,
            fill=(255, 255, 255),
            font=font_big,
        )
        draw.text(
            (text_x, height // 2 + 45),
            config.WELCOME_CARD_SUBTITLE.format(count=member.guild.member_count),
            fill=(180, 180, 180),
            font=font_small,
        )

        draw.rectangle(
            [text_x, height // 2 + 90, width - 60, height // 2 + 93],
            fill=accent,
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    except Exception as e:
        log.exception("فشل إنشاء Welcome Card: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════
# 📊 القسم 8: إحصائيات السيرفر
# ═══════════════════════════════════════════════════════════════

_last_stats_update = 0.0


async def update_guild_stats(guild: discord.Guild):
    """يحدّث اسم روم الإحصائيات"""
    global _last_stats_update

    if not config.STATS_ENABLED:
        return

    now = time.time()
    if now - _last_stats_update < 60:
        return
    _last_stats_update = now

    ch = guild.get_channel(config.CH_STATS.get("id"))
    if not ch:
        for name in config.CH_STATS["names"]:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                break
    if not ch:
        return

    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    channels_count = len(guild.channels)
    roles_count = len(guild.roles)

    new_name = (
        "Members: " + str(total) + " | "
        "Humans: " + str(humans) + " | "
        "Bots: " + str(bots) + " | "
        "Ch: " + str(channels_count) + " | "
        "Roles: " + str(roles_count)
    )

    if len(new_name) > 100:
        new_name = "Members: " + str(total) + " | H: " + str(humans) + " | B: " + str(bots)

    try:
        if ch.name != new_name:
            await ch.edit(name=new_name, reason="تحديث الإحصائيات")
    except discord.Forbidden:
        log.warning("لا أملك صلاحية تعديل اسم روم الإحصائيات")
    except Exception as e:
        log.warning("فشل تحديث الإحصائيات: %s", e)


# ═══════════════════════════════════════════════════════════════
# 💾 القسم 9: النسخ الاحتياطية الدورية
# ═══════════════════════════════════════════════════════════════

async def periodic_backup_loop(bot: commands.Bot):
    """يأخذ نسخة احتياطية كل X ساعة"""
    await bot.wait_until_ready()
    log.info("حلقة النسخ الدورية بدأت (كل %d ساعة)", config.PERIODIC_BACKUP_HOURS)

    while True:
        try:
            await asyncio.sleep(config.PERIODIC_BACKUP_HOURS * 3600)

            cache_full = SHARED.get("cache_full_guild")
            backup_name = SHARED.get("backup_guild_name")
            backup_icon = SHARED.get("backup_guild_icon")
            backup_banner = SHARED.get("backup_guild_banner")

            for guild in bot.guilds:
                try:
                    if cache_full:
                        await cache_full(guild)
                    if backup_name:
                        backup_name(guild)
                    if backup_icon:
                        await backup_icon(guild)
                    if backup_banner:
                        await backup_banner(guild)
                    log.info("نسخة احتياطية دورية: %s", guild.name)
                except Exception as e:
                    log.warning("فشل النسخ الاحتياطي لـ %s: %s", guild.name, e)

        except Exception as e:
            log.exception("خطأ في periodic_backup_loop: %s", e)

# ═══════════════════════════════════════════════════════════════
# 🔄 القسم 9.5: تجديد البانلات التلقائي
# ═══════════════════════════════════════════════════════════════

async def auto_refresh_panels_loop(bot: commands.Bot):
    """
    كل X دقيقة:
    - يحذف البانلات القديمة (التذاكر + التقديم)
    - يرسل بانلات جديدة
    - يضمن أن الأزرار شغالة دائماً
    """
    await bot.wait_until_ready()
    log.info("حلقة تجديد البانلات بدأت (كل %d دقيقة)",
             config.PANEL_AUTO_REFRESH_MINUTES)

    while True:
        try:
            await asyncio.sleep(config.PANEL_AUTO_REFRESH_MINUTES * 60)

            get_ticket_panel = SHARED.get("get_ch_ticket_panel")
            get_apply_panel = SHARED.get("get_ch_apply_panel")

            for guild in bot.guilds:
                # ---------- بانل التذاكر ----------
                if get_ticket_panel:
                    try:
                        ch = get_ticket_panel(guild)
                        if ch:
                            # احذف القديم
                            deleted = 0
                            async for msg in ch.history(limit=50):
                                if msg.author == bot.user and msg.embeds:
                                    for emb in msg.embeds:
                                        if emb.title and "مركز الدعم" in emb.title:
                                            try:
                                                await msg.delete()
                                                deleted += 1
                                            except Exception:
                                                pass
                                            break

                            # أرسل الجديد
                            from main import TicketButtonView
                            embed = discord.Embed(
                                title="مركز الدعم الفني",
                                description="اضغط على الزر أدناه لفتح تذكرة خاصة للتواصل مع الإدارة.",
                                color=discord.Color.green(),
                            )
                            await ch.send(embed=embed, view=TicketButtonView())
                            log.info("تم تجديد بانل التذاكر في %s (حذف %d)",
                                     guild.name, deleted)
                    except Exception as e:
                        log.warning("فشل تجديد بانل التذاكر: %s", e)

                # ---------- بانل التقديم ----------
                if get_apply_panel:
                    try:
                        ch = get_apply_panel(guild)
                        if ch:
                            deleted = 0
                            async for msg in ch.history(limit=50):
                                if msg.author == bot.user and msg.embeds:
                                    for emb in msg.embeds:
                                        if emb.title and "التقديم للسيرفر" in emb.title:
                                            try:
                                                await msg.delete()
                                                deleted += 1
                                            except Exception:
                                                pass
                                            break

                            from main import ApplicationButtonView
                            embed = discord.Embed(
                                title="التقديم للسيرفر",
                                description="اضغط على الزر أدناه لتعبئة استمارة التقديم.",
                                color=discord.Color.purple(),
                            )
                            await ch.send(embed=embed, view=ApplicationButtonView())
                            log.info("تم تجديد بانل التقديم في %s (حذف %d)",
                                     guild.name, deleted)
                    except Exception as e:
                        log.warning("فشل تجديد بانل التقديم: %s", e)

        except Exception as e:
            log.exception("خطأ في auto_refresh_panels_loop: %s", e)

# ═══════════════════════════════════════════════════════════════
# ⚙️ القسم 10: الأوامر
# ═══════════════════════════════════════════════════════════════

def setup_commands(bot: commands.Bot):
    """تسجيل كل أوامر extras"""

    @bot.tree.command(name="تذكير", description="ضع تذكيرا بعد مدة محددة")
    @app_commands.describe(
        duration="المدة (مثل: 10m / 2h / 1d / 1h30m)",
        text="نص التذكير",
    )
    async def remind_cmd(interaction: discord.Interaction,
                         duration: str, text: str):
        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message(
                "صيغة المدة غير صحيحة. أمثلة: 10m / 2h / 1d / 1h30m",
                ephemeral=True,
            )
            return

        if seconds > 30 * 86400:
            await interaction.response.send_message(
                "الحد الأقصى 30 يوم.", ephemeral=True
            )
            return

        check_rl = SHARED.get("check_rate_limit")
        if check_rl:
            ok, wait = check_rl(interaction.user.id, "تذكير")
            if not ok:
                await interaction.response.send_message(
                    "تجاوزت الحد. انتظر " + str(wait) + " ثانية.", ephemeral=True
                )
                return

        due_time = time.time() + seconds
        reminder = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "text": text,
            "due": due_time,
            "original_link": getattr(interaction.channel, "jump_url", None),
        }
        REMINDERS.append(reminder)
        await save_reminders()

        await interaction.response.send_message(
            "سأذكرك بعد " + format_duration(seconds) + ".",
            ephemeral=True,
        )

    @bot.tree.command(name="حجر_موقت", description="حجر مؤقت مع فك تلقائي")
    @app_commands.describe(
        member="العضو",
        duration="المدة (مثل: 1h / 1d / 7d)",
        reason="السبب",
    )
    async def tempjail_cmd(interaction: discord.Interaction,
                           member: discord.Member,
                           duration: str,
                           reason: str = "لم يحدد"):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message(
                "صيغة غير صحيحة. أمثلة: 1h / 1d / 7d", ephemeral=True
            )
            return

        if seconds > 30 * 86400:
            await interaction.response.send_message(
                "الحد 30 يوم.", ephemeral=True
            )
            return

        apply_jail = SHARED.get("apply_jail")
        if not apply_jail:
            await interaction.response.send_message(
                "خطأ داخلي.", ephemeral=True
            )
            return

        ok, msg = await apply_jail(
            interaction.guild, member,
            "حجر مؤقت (" + format_duration(seconds) + ") بواسطة "
            + str(interaction.user) + ": " + reason,
        )

        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        TEMP_ACTIONS.append({
            "guild_id": interaction.guild.id,
            "user_id": member.id,
            "type": "jail",
            "until": time.time() + seconds,
            "moderator": interaction.user.id,
            "reason": reason,
        })
        await save_temp_actions()

        try:
            await member.send(
                "حجر مؤقت من " + interaction.guild.name + "\n"
                "المدة: " + format_duration(seconds) + "\n"
                "السبب: " + reason
            )
        except Exception:
            pass

        get_ch = SHARED.get("get_ch_admin_review")
        if get_ch:
            ch = get_ch(interaction.guild)
            if ch:
                embed = discord.Embed(
                    title="حجر مؤقت",
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(
                    name="العضو",
                    value=str(member) + " (" + str(member.id) + ")",
                    inline=False,
                )
                embed.add_field(
                    name="بواسطة",
                    value=interaction.user.mention,
                    inline=False,
                )
                embed.add_field(
                    name="المدة",
                    value=format_duration(seconds),
                    inline=True,
                )
                embed.add_field(name="السبب", value=reason, inline=False)
                try:
                    await ch.send(embed=embed)
                except Exception:
                    pass

        await interaction.response.send_message(
            msg + "\nالمدة: " + format_duration(seconds),
            ephemeral=True,
        )

    @bot.tree.command(name="قائمة_الحجر_الموقت",
                      description="عرض العقوبات المؤقتة النشطة")
    async def temp_list_cmd(interaction: discord.Interaction):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        guild_actions = [
            a for a in TEMP_ACTIONS if a["guild_id"] == interaction.guild.id
        ]

        if not guild_actions:
            await interaction.response.send_message(
                "لا توجد عقوبات مؤقتة نشطة.", ephemeral=True
            )
            return

        lines = []
        now = time.time()
        for a in guild_actions[:20]:
            remaining = int(a["until"] - now)
            lines.append(
                "<@" + str(a["user_id"]) + "> -- تبقى: " + format_duration(remaining)
            )

        embed = discord.Embed(
            title="العقوبات المؤقتة",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="تحديث_الاحصائيات",
                      description="تحديث روم الإحصائيات يدويا")
    async def update_stats_cmd(interaction: discord.Interaction):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        global _last_stats_update
        _last_stats_update = 0

        await update_guild_stats(interaction.guild)
        await interaction.response.send_message(
            "تم تحديث الإحصائيات.", ephemeral=True
        )

    @bot.tree.command(name="نسخة_الان",
                      description="أخذ نسخة احتياطية الآن")
    async def backup_now_cmd(interaction: discord.Interaction):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        cache_full = SHARED.get("cache_full_guild")
        backup_name = SHARED.get("backup_guild_name")
        backup_icon = SHARED.get("backup_guild_icon")
        backup_banner = SHARED.get("backup_guild_banner")

        try:
            if cache_full:
                await cache_full(interaction.guild)
            if backup_name:
                backup_name(interaction.guild)
            if backup_icon:
                await backup_icon(interaction.guild)
            if backup_banner:
                await backup_banner(interaction.guild)

            await interaction.followup.send(
                "تم أخذ نسخة احتياطية كاملة.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send("فشل: " + str(e), ephemeral=True)

    @bot.tree.command(name="اختبار_اوتو_مود",
                      description="اختبار فحص Auto-Mod على نص")
    @app_commands.describe(text="النص للفحص")
    async def automod_test_cmd(interaction: discord.Interaction, text: str):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        class FakeMessage:
            def __init__(self, content):
                self.content = content
                self.mentions = []

        result = automod_check(FakeMessage(text))
        if result:
            embed = discord.Embed(
                title="Auto-Mod يكشف مخالفة",
                description="السبب: " + result["reason"] + "\n"
                            "الإجراء: " + result["action"] + "\n"
                            "التفاصيل: " + result["detail"],
                color=discord.Color.orange(),
            )
        else:
            embed = discord.Embed(
                title="النص سليم",
                description="Auto-Mod لم يجد أي مخالفة.",
                color=discord.Color.green(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="اختبار_التصيد",
                      description="فحص رابط للتصيد")
    @app_commands.describe(text="النص للفحص")
    async def phishing_test_cmd(interaction: discord.Interaction, text: str):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        result = detect_phishing(text)
        if result:
            embed = discord.Embed(
                title="رابط تصيد مكتشف!",
                description=result,
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="الرابط سليم",
                color=discord.Color.green(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ═══════════════════════════════════════════════════════════════
# 💬 القسم 11: معالج الرسائل (Anti-Phishing + Auto-Mod)
# ═══════════════════════════════════════════════════════════════

def setup_message_handler(bot: commands.Bot):
    """يسجل معالج on_message جديد يعمل قبل الموجود في main.py"""
    old_handler = bot.on_message

    async def new_message_handler(message: discord.Message):
        if message.author.bot or not message.guild:
            if old_handler:
                await old_handler(message)
            return

        # ✅ تجاهل الصور/الملصقات الفارغة (بدون نص)
        has_media = bool(message.attachments or message.stickers)
        has_text = bool((message.content or "").strip())

        if has_media and not has_text:
            # صورة/ملصق فقط -> تجاهل كلي
            if old_handler:
                await old_handler(message)
            return

        is_exempted = SHARED.get("is_exempted")
        if is_exempted and is_exempted(message.author):
            if old_handler:
                await old_handler(message)
            return

        guild = message.guild
        member = message.author

        # ---------- Anti-Phishing ----------
        if config.ANTI_PHISHING_ENABLED:
            phishing_url = detect_phishing(message.content or "")
            if phishing_url:
                try:
                    await message.delete()
                except Exception:
                    pass

                get_ch = SHARED.get("get_ch_admin_review")
                log_ch = get_ch(guild) if get_ch else None

                punishment_msg = ""
                apply_jail = SHARED.get("apply_jail")
                if apply_jail:
                    ok, msg = await apply_jail(
                        guild, member,
                        "Anti-Phishing: " + phishing_url
                    )
                    punishment_msg = msg

                if log_ch:
                    embed = discord.Embed(
                        title="Anti-Phishing: تم كشف رابط تصيد",
                        color=discord.Color.dark_red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.set_author(
                        name=str(member),
                        icon_url=member.display_avatar.url,
                    )
                    embed.add_field(
                        name="العضو",
                        value=str(member) + " (" + str(member.id) + ")",
                        inline=False,
                    )
                    embed.add_field(
                        name="الرابط المشبوه",
                        value=phishing_url,
                        inline=False,
                    )
                    embed.add_field(
                        name="الرسالة",
                        value=(message.content or "")[:500],
                        inline=False,
                    )
                    embed.add_field(
                        name="العقوبة",
                        value=punishment_msg or "حجر",
                        inline=False,
                    )
                    try:
                        await log_ch.send(embed=embed)
                    except Exception:
                        pass

                log.warning("Phishing detected: %s -> %s", member, phishing_url)
                return

        # ---------- Auto-Mod ----------
        if config.AUTOMOD_ENABLED:
            # ✅ تجاهل الصور/الملصقات إذا ما كان فيه نص
            # (نفحص النص دائماً — حتى لو فيه صورة)
            if not has_text:
                if old_handler:
                    await old_handler(message)
                return

            result = automod_check(message)
            if result:
                try:
                    await message.delete()
                except Exception:
                    pass

                reason = result["reason"]
                action = result["action"]
                detail = result["detail"]

                action_taken = "حذف الرسالة"

                if action == "warn":
                    USER_WARNINGS = SHARED.get("USER_WARNINGS")
                    save_warnings = SHARED.get("save_warnings")

                    if USER_WARNINGS is not None:
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        USER_WARNINGS.setdefault(member.id, []).append({
                            "reason": "Auto-Mod: " + reason + " (" + detail + ")",
                            "warned_by": "Auto-Mod",
                            "date": now_str,
                        })
                        if save_warnings:
                            await save_warnings()
                        warn_count = len(USER_WARNINGS[member.id])
                        action_taken = "تحذير رقم " + str(warn_count)

                        if warn_count >= 3:
                            apply_jail = SHARED.get("apply_jail")
                            if apply_jail:
                                ok, msg = await apply_jail(
                                    guild, member,
                                    "Auto-Mod: بلوغ " + str(warn_count) + " تحذيرات"
                                )
                                action_taken += "\n" + msg + " (حجر دائم)"

                    try:
                        await member.send(
                            "تنبيه Auto-Mod من " + guild.name + "\n"
                            "السبب: " + reason + " (" + detail + ")\n"
                            "الإجراء: " + action_taken
                        )
                    except Exception:
                        pass

                elif action == "timeout":
                    try:
                        until = discord.utils.utcnow() + datetime.timedelta(minutes=10)
                        await member.timeout(
                            until,
                            reason="Auto-Mod: " + reason + " (" + detail + ")"
                        )
                        action_taken = "تايم آوت 10 دقائق"
                    except Exception as e:
                        action_taken = "فشل التايم آوت: " + str(e)

                elif action == "delete_only":
                    action_taken = "حذف الرسالة فقط"

                get_ch = SHARED.get("get_ch_admin_review")
                log_ch = get_ch(guild) if get_ch else None
                if log_ch:
                    embed = discord.Embed(
                        title="Auto-Mod: مخالفة تلقائية",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.set_author(
                        name=str(member),
                        icon_url=member.display_avatar.url,
                    )
                    embed.add_field(
                        name="العضو",
                        value=str(member) + " (" + str(member.id) + ")",
                        inline=False,
                    )
                    embed.add_field(
                        name="الروم",
                        value=message.channel.mention,
                        inline=True,
                    )
                    embed.add_field(
                        name="النوع",
                        value=reason,
                        inline=True,
                    )
                    embed.add_field(
                        name="التفاصيل",
                        value=detail,
                        inline=True,
                    )
                    embed.add_field(
                        name="الإجراء",
                        value=action_taken,
                        inline=False,
                    )
                    content = (message.content or "")[:500]
                    embed.add_field(
                        name="الرسالة",
                        value=content,
                        inline=False,
                    )
                    try:
                        await log_ch.send(embed=embed)
                    except Exception:
                        pass

                log.info("Auto-Mod: %s -> %s (%s)", member, reason, action_taken)
                return

        if old_handler:
            await old_handler(message)

    bot.remove_listener(new_message_handler, "on_message")
    bot.add_listener(new_message_handler, "on_message")


# ═══════════════════════════════════════════════════════════════
# 🚀 القسم 12: load_extras() — نقطة التحميل
# ═══════════════════════════════════════════════════════════════

def load_extras(bot: commands.Bot, shared: dict):
    """يُحمّل كل الإضافات"""
    SHARED.clear()
    SHARED.update(shared)

    load_reminders()
    load_temp_actions()

    setup_commands(bot)
    setup_message_handler(bot)

    # ---------- Welcome Card ----------
    async def welcome_card_handler(member: discord.Member):
        if not config.WELCOME_CARD_ENABLED:
            return

        get_ch_welcome = SHARED.get("get_ch_welcome")
        if not get_ch_welcome:
            return

        ch = get_ch_welcome(member.guild)
        if not ch:
            return

        card = await make_welcome_card(member)
        if card:
            try:
                await ch.send(
                    content="Welcome " + member.mention,
                    file=discord.File(card, filename="welcome.png"),
                )
                return
            except Exception as e:
                log.warning("فشل إرسال Welcome Card: %s", e)

        embed = discord.Embed(
            title="عضو جديد!",
            description="مرحبا " + member.mention + " في " + member.guild.name,
            color=discord.Color.brand_green(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await ch.send(content=member.mention, embed=embed)
        except Exception:
            pass

    bot.add_listener(welcome_card_handler, "on_member_join")

    # ---------- بدء المهام عند on_ready ----------
    async def start_tasks_on_ready():
        if getattr(bot, "_extras_started", False):
            return
        bot._extras_started = True

        log.info("بدء تشغيل مهام extras...")

        # اسحب البيانات من MongoDB قبل تشغيل الحلقات
        await sync_reminders_from_mongo()
        await sync_temp_actions_from_mongo()

        asyncio.create_task(reminder_loop(bot))
        asyncio.create_task(temp_actions_loop(bot))

        # ← تجديد البانلات
        if config.PANEL_AUTO_REFRESH:
            asyncio.create_task(auto_refresh_panels_loop(bot))
        if config.PERIODIC_BACKUP_ENABLED:
            asyncio.create_task(periodic_backup_loop(bot))

        async def stats_loop():
            while True:
                try:
                    for guild in bot.guilds:
                        await update_guild_stats(guild)
                except Exception as e:
                    log.warning("خطأ في stats_loop: %s", e)
                await asyncio.sleep(config.STATS_UPDATE_MINUTES * 60)

        asyncio.create_task(stats_loop())

        log.info("تم بدء كل المهام بنجاح")

    bot.add_listener(start_tasks_on_ready, "on_ready")

    log.info("تم تحميل extras.py -- كل الإضافات شغالة")

# ═══════════════════════════════════════════════════════════════
# 🔄 القسم 17: تجديد البانلات التلقائي
# ═══════════════════════════════════════════════════════════════
# البوت يحذف البانلات القديمة ويرسل جديدة كل X دقيقة
PANEL_AUTO_REFRESH = True
PANEL_AUTO_REFRESH_MINUTES = 60  # كل ساعة (تقدر تغيره)



# ═══════════════════════════════════════════════════════════════
# 🔎 القسم 19: اكتشاف اليوزرات
# ═══════════════════════════════════════════════════════════════
# تشغيل/إطفاء الميزة
USERNAME_FINDER_ENABLED = True

# مفتاح Gemini (يُقرأ من Render Environment)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# المنصات المدعومة (socialscan)
# المتاح: Instagram, Twitter, Snapchat, Reddit, Pinterest, GitHub
USERNAME_FINDER_PLATFORMS = [
    "Instagram",
    "Twitter",
    "Snapchat",
]

# ⭐ آيدي الروم المخصص للأمر
# اتركه 0 لو تبي الأمر يعمل في أي روم
# ⚠️ استبدله بآيدي رومك (انسخه من Discord)
USERNAME_FINDER_CHANNEL_ID = 0
