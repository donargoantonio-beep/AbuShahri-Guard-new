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

# SHARED: يمتلئ من main.py بالدوال والكائنات المشتركة
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
    """
    يحوّل نص مثل 10m / 2h / 1d / 30s إلى ثواني.
    يدعم الجمع: 1h30m
    يدعم العربي: 1 ساعة 30 دقيقة
    """
    if not text:
        return None

    pattern = re.compile(
        r"(\d+)\s*(d|h|m|s|يوم|ساعة|دقيقة|ثانية)",
        re.IGNORECASE,
    )
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
    """تحميل التذكيرات من الملف"""
    global REMINDERS
    REMINDERS = _load_json(config.REMINDERS_FILE, [])


def save_reminders():
    """حفظ التذكيرات في الملف"""
    _save_json(config.REMINDERS_FILE, REMINDERS)


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
                save_reminders()

        except Exception as e:
            log.exception("خطأ في reminder_loop: %s", e)

        await asyncio.sleep(30)


# ═══════════════════════════════════════════════════════════════
# 🔒 القسم 4: نظام الحجر المؤقت
# ═══════════════════════════════════════════════════════════════

TEMP_ACTIONS: list = []


def load_temp_actions():
    """تحميل العقوبات المؤقتة من الملف"""
    global TEMP_ACTIONS
    TEMP_ACTIONS = _load_json(config.TEMP_ACTIONS_FILE, [])


def save_temp_actions():
    """حفظ العقوبات المؤقتة في الملف"""
    _save_json(config.TEMP_ACTIONS_FILE, TEMP_ACTIONS)


async def temp_actions_loop(bot: commands.Bot):
    """
    حلقة تتحقق كل 30 ثانية من العقوبات المؤقتة المنتهية.
    - تفك الحجر تلقائياً
    - ترسل إشعار في admin-review
    """
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
                        log.warning("السيرفر غير موجود: %s", action["guild_id"])
                        if action in TEMP_ACTIONS:
                            TEMP_ACTIONS.remove(action)
                        continue

                    user_id = action["user_id"]
                    kind = action["type"]
                    member = guild.get_member(user_id)

                    # --- فك الحجر ---
                    if kind == "jail":
                        if member is None:
                            log.warning("العضو %s ليس في السيرفر -- تخطي", user_id)
                        else:
                            remove_jail = SHARED.get("remove_jail")
                            if remove_jail:
                                ok, msg = await remove_jail(guild, member)
                                log.info("فك حجر %s: %s", member, msg)
                            else:
                                log.error("remove_jail غير موجود في SHARED!")

                    # --- إشعار الإدارة ---
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
                save_temp_actions()
                log.info("تم إنهاء %d عقوبة مؤقتة", len(due))

        except Exception as e:
            log.exception("خطأ في temp_actions_loop: %s", e)

        await asyncio.sleep(30)
        # ═══════════════════════════════════════════════════════════════
# 🎣 القسم 5: Anti-Phishing
# ═══════════════════════════════════════════════════════════════

# --- regex لاستخراج الروابط ---
PHISHING_PATTERN = re.compile(
    r"(https?://)?([a-z0-9\-\.]+\.[a-z]{2,})(/[^\s]*)?",
    re.IGNORECASE,
)


def detect_phishing(content: str) -> Optional[str]:
    """
    يفحص النص ويعيد:
    - اسم النطاق المشبوه إذا وجد
    - "keyword: X + رابط" إذا كانت كلمة مشبوهة مع رابط
    - None إذا سليم
    """
    if not content:
        return None

    lower = content.lower()

    # 1. فحص النطاقات المعروفة
    for domain in config.PHISHING_DOMAINS:
        if domain in lower:
            return domain

    # 2. فحص كلمات مفتاحية + رابط
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
                # تأكد أنه مو النطاق الرسمي
                if not any(official in domain for official in [
                    "discord.com", "discord.gg", "discordapp.com",
                    "steampowered.com", "steamcommunity.com",
                    "twitch.tv",
                ]):
                    return domain

    return None


# ═══════════════════════════════════════════════════════════════
# 🛡️ القسم 6: Auto-Mod (كشف السبام)
# ═══════════════════════════════════════════════════════════════

# --- regex للإيموجي ---
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002700-\U000027BF"   # dingbats
    "\U0001F900-\U0001F9FF"   # supplemental
    "\U00002600-\U000026FF"   # misc symbols
    "\U0001FA70-\U0001FAFF"   # symbols extended
    "]+",
    flags=re.UNICODE,
)

# --- regex لـ Zalgo (رموز مشوهة) ---
ZALGO_RE = re.compile(
    r"[\u0300-\u036f\u0489\u1ab0-\u1aff"
    r"\u1dc0-\u1dff\u20d0-\u20ff\ufe20-\ufe2f]"
)


def count_emojis(text: str) -> int:
    """يعد الإيموجي في النص (بما فيها إيموجي السيرفر المخصص)"""
    count = 0
    for match in EMOJI_PATTERN.finditer(text):
        count += len(match.group(0))
    # إيموجي مخصص <:name:id>
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
    """يعد الرموز المشوهة (Zalgo)"""
    return len(ZALGO_RE.findall(text))


def automod_check(message) -> Optional[dict]:
    """
    يفحص الرسالة ويرجع:
    - None إذا سليمة
    - dict {reason, action, detail} إذا مخالفة
    """
    if not config.AUTOMOD_ENABLED:
        return None

    s = config.AUTOMOD_SETTINGS
    content = message.content or ""

    # 1. إيموجي
    if count_emojis(content) > s["max_emojis"]:
        return {
            "reason": "spam_emoji",
            "action": s["emoji_action"],
            "detail": str(count_emojis(content)) + " إيموجي",
        }

    # 2. حروف كبيرة
    if len(content) >= s["caps_min_length"] and caps_percent(content) > s["max_caps_percent"]:
        return {
            "reason": "spam_caps",
            "action": s["caps_action"],
            "detail": str(int(caps_percent(content) * 100)) + "% حروف كبيرة",
        }

    # 3. منشنات
    if len(message.mentions) > s["max_mentions"]:
        return {
            "reason": "spam_mentions",
            "action": s["mentions_action"],
            "detail": str(len(message.mentions)) + " منشن",
        }

    # 4. Zalgo
    if count_zalgo(content) > s["max_zalgo"]:
        return {
            "reason": "zalgo",
            "action": s["zalgo_action"],
            "detail": str(count_zalgo(content)) + " رمز مشوه",
        }

    # 5. رموز
    if len(content) >= 10 and symbol_percent(content) > s["max_symbols_percent"]:
        return {
            "reason": "spam_symbols",
            "action": s["symbols_action"],
            "detail": str(int(symbol_percent(content) * 100)) + "% رموز",
        }

    return None


# ═══════════════════════════════════════════════════════════════
# 👋 القسم 7: Welcome Card (صورة الترحيب)
# ═══════════════════════════════════════════════════════════════

def _wrap_text(text: str, max_chars: int = 20) -> str:
    """يقص النص الطويل"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "..."


async def make_welcome_card(member: discord.Member) -> Optional[io.BytesIO]:
    """
    ينشئ صورة ترحيب بالأفاتار والاسم.
    يرجع BytesIO أو None إذا فشل.
    يحتاج مكتبة Pillow.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        log.warning("Pillow غير مثبتة -- Welcome Card معطل")
        return None

    try:
        width, height = config.WELCOME_CARD_SIZE
        bg_color = config.WELCOME_CARD_BG_COLOR
        accent = config.WELCOME_CARD_ACCENT

        # --- الخلفية ---
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # --- دائرة الأفاتار ---
        circle_x = 150
        circle_y = height // 2
        circle_r = 100

        # حلقة خارجية
        draw.ellipse(
            [
                circle_x - circle_r - 5, circle_y - circle_r - 5,
                circle_x + circle_r + 5, circle_y + circle_r + 5,
            ],
            fill=accent,
        )

        # --- تحميل الأفاتار ---
        avatar_bytes = await member.display_avatar.replace(
            size=256, format="png"
        ).read()

        avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar_img = avatar_img.resize((circle_r * 2, circle_r * 2), Image.LANCZOS)

        # --- قناع دائري ---
        mask = Image.new("L", (circle_r * 2, circle_r * 2), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, circle_r * 2, circle_r * 2], fill=255)

        # --- لصق الأفاتار ---
        img.paste(avatar_img, (circle_x - circle_r, circle_y - circle_r), mask)

        # --- تحميل خط ---
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

        # --- كتابة النصوص ---
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

        # --- خط أسفل ---
        draw.rectangle(
            [text_x, height // 2 + 90, width - 60, height // 2 + 93],
            fill=accent,
        )

        # --- حفظ ---
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

# الحد الأدنى بين التحديثات (Discord rate limit)
_last_stats_update = 0.0


async def update_guild_stats(guild: discord.Guild):
    """
    يحدّث اسم روم الإحصائيات بآخر الأرقام.
    يعمل مرة واحدة كل 60 ثانية (rate limit).
    """
    global _last_stats_update

    if not config.STATS_ENABLED:
        return

    now = time.time()
    if now - _last_stats_update < 60:
        return
    _last_stats_update = now

    # --- إيجاد الروم ---
    ch = guild.get_channel(config.CH_STATS.get("id"))
    if not ch:
        for name in config.CH_STATS["names"]:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                break
    if not ch:
        return

    # --- حساب الإحصائيات ---
    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    channels_count = len(guild.channels)
    roles_count = len(guild.roles)

    # --- بناء الاسم الجديد ---
    new_name = (
        "Members: " + str(total) + " | "
        "Humans: " + str(humans) + " | "
        "Bots: " + str(bots) + " | "
        "Ch: " + str(channels_count) + " | "
        "Roles: " + str(roles_count)
    )

    # Discord max 100 حرف
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
    """
    يأخذ نسخة احتياطية كاملة كل X ساعة (حسب config)
    يشمل: cache الرومات والرتب + اسم/أيقونة/بانر السيرفر
    """
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
# ⚙️ القسم 10: الأوامر
# ═══════════════════════════════════════════════════════════════

def setup_commands(bot: commands.Bot):
    """تسجيل كل أوامر extras"""

    # --- أمر /تذكير ---
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

        # Rate limiting
        check_rl = SHARED.get("check_rate_limit")
        if check_rl:
            ok, wait = check_rl(interaction.user.id, "تذكير")
            if not ok:
                await interaction.response.send_message(
                    "تجاوزت الحد. انتظر " + str(wait) + " ثانية.", ephemeral=True
                )
                return

        # أضف التذكير
        due_time = time.time() + seconds
        reminder = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "text": text,
            "due": due_time,
            "original_link": getattr(interaction.channel, "jump_url", None),
        }
        REMINDERS.append(reminder)
        save_reminders()

        await interaction.response.send_message(
            "سأذكرك بعد " + format_duration(seconds) + ".",
            ephemeral=True,
        )

    # --- أمر /حجر_موقت ---
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

        # طبّق الحجر
        ok, msg = await apply_jail(
            interaction.guild, member,
            "حجر مؤقت (" + format_duration(seconds) + ") بواسطة "
            + str(interaction.user) + ": " + reason,
        )

        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # سجّل العقوبة المؤقتة
        TEMP_ACTIONS.append({
            "guild_id": interaction.guild.id,
            "user_id": member.id,
            "type": "jail",
            "until": time.time() + seconds,
            "moderator": interaction.user.id,
            "reason": reason,
        })
        save_temp_actions()

        # إشعار العضو
        try:
            await member.send(
                "حجر مؤقت من " + interaction.guild.name + "\n"
                "المدة: " + format_duration(seconds) + "\n"
                "السبب: " + reason
            )
        except Exception:
            pass

        # لوق
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

    # --- أمر /قائمة_الحجر_الموقت ---
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

    # --- أمر /تحديث_الاحصائيات ---
    @bot.tree.command(name="تحديث_الاحصائيات",
                      description="تحديث روم الإحصائيات يدويا")
    async def update_stats_cmd(interaction: discord.Interaction):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        global _last_stats_update
        _last_stats_update = 0  # تجاوز الـ cooldown

        await update_guild_stats(interaction.guild)
        await interaction.response.send_message(
            "تم تحديث الإحصائيات.", ephemeral=True
        )

    # --- أمر /نسخة_الان ---
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

    # --- أمر /اختبار_اوتو_مود ---
    @bot.tree.command(name="اختبار_اوتو_مود",
                      description="اختبار فحص Auto-Mod على نص")
    @app_commands.describe(text="النص للفحص")
    async def automod_test_cmd(interaction: discord.Interaction, text: str):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        # كائن وهمي للفحص
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

    # --- أمر /اختبار_التصيد ---
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
    """
    يسجل معالج on_message جديد يعمل قبل الموجود في main.py.
    يفحص:
    1. Anti-Phishing -> حجر
    2. Auto-Mod -> حسب الإعدادات
    """
    old_handler = bot.on_message

    async def new_message_handler(message: discord.Message):
        # تجاهل
        if message.author.bot or not message.guild:
            if old_handler:
                await old_handler(message)
            return

        # تجاهل المستثنين
        is_exempted = SHARED.get("is_exempted")
        if is_exempted and is_exempted(message.author):
            if old_handler:
                await old_handler(message)
            return

        guild = message.guild
        member = message.author

        # ============================================================
        # فحص Anti-Phishing
        # ============================================================
        if config.ANTI_PHISHING_ENABLED:
            phishing_url = detect_phishing(message.content or "")
            if phishing_url:
                # احذف الرسالة
                try:
                    await message.delete()
                except Exception:
                    pass

                # طبّق الحجر
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

                # لوق
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

        # ============================================================
        # فحص Auto-Mod
        # ============================================================
        if config.AUTOMOD_ENABLED:
            result = automod_check(message)
            if result:
                # احذف الرسالة
                try:
                    await message.delete()
                except Exception:
                    pass

                reason = result["reason"]
                action = result["action"]
                detail = result["detail"]

                action_taken = "حذف الرسالة"

                # --- warn ---
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

                        # 3 تحذيرات = حجر دائم
                        if warn_count >= 3:
                            apply_jail = SHARED.get("apply_jail")
                            if apply_jail:
                                ok, msg = await apply_jail(
                                    guild, member,
                                    "Auto-Mod: بلوغ " + str(warn_count) + " تحذيرات"
                                )
                                action_taken += "\n" + msg + " (حجر دائم)"

                    # إشعار العضو
                    try:
                        await member.send(
                            "تنبيه Auto-Mod من " + guild.name + "\n"
                            "السبب: " + reason + " (" + detail + ")\n"
                            "الإجراء: " + action_taken
                        )
                    except Exception:
                        pass

                # --- timeout ---
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

                # --- delete_only ---
                elif action == "delete_only":
                    action_taken = "حذف الرسالة فقط"

                # لوق
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

        # اترك main.py يكمل
        if old_handler:
            await old_handler(message)

    bot.remove_listener(new_message_handler, "on_message")
    bot.add_listener(new_message_handler, "on_message")


# ═══════════════════════════════════════════════════════════════
# 🚀 القسم 12: load_extras() — نقطة التحميل
# ═══════════════════════════════════════════════════════════════

def load_extras(bot: commands.Bot, shared: dict):
    """
    يُحمّل كل الإضافات:
    - يربط SHARED
    - يحمّل الملفات
    - يسجل الأوامر
    - يسجل معالج الرسائل
    - يسجل welcome card
    - يشغّل المهام الدورية عند on_ready
    """
    # اربط SHARED
    SHARED.clear()
    SHARED.update(shared)

    # حمّل الملفات
    load_reminders()
    load_temp_actions()

    # سجل الأوامر
    setup_commands(bot)

    # سجل معالج الرسائل
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

        # جرّب ترسل الصورة
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

        # احتياطي: embed عادي
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
        # تجنب التشغيل المتكرر
        if getattr(bot, "_extras_started", False):
            return
        bot._extras_started = True

        log.info("بدء تشغيل مهام extras...")

        # 1. التذكيرات
        asyncio.create_task(reminder_loop(bot))

        # 2. العقوبات المؤقتة
        asyncio.create_task(temp_actions_loop(bot))

        # 3. النسخ الدورية
        if config.PERIODIC_BACKUP_ENABLED:
            asyncio.create_task(periodic_backup_loop(bot))

        # 4. الإحصائيات
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
