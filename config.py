"""
╔══════════════════════════════════════════════════════════════╗
║  config.py — كل إعدادات البوت في مكان واحد                  ║
║  الإصدار: 5.1                                                ║
╚══════════════════════════════════════════════════════════════╝
"""

# ============================================================
# 👑 مالك البوت
# ============================================================
BOT_OWNER_ID = 813236200142929950


# ============================================================
# 📁 المسارات والملفات
# ============================================================
DATA_DIR     = "data"
BACKUPS_DIR  = "data/backups"
ICONS_DIR    = "data/backups/icons"
BANNERS_DIR  = "data/backups/banners"
LOGS_DIR     = "logs"
CARDS_DIR    = "data/welcome_cards"

WARNINGS_FILE      = "data/warnings.json"
STATE_FILE         = "data/state.json"
ANTINUKE_FILE      = "data/antinuke.json"
BACKUP_FILE        = "data/backup_meta.json"
GUILD_CACHE_FILE   = "data/guild_cache.json"
REMINDERS_FILE     = "data/reminders.json"
TEMP_ACTIONS_FILE  = "data/temp_actions.json"
AUTOMOD_FILE       = "data/automod.json"
BOT_LOG_FILE       = "logs/bot.log"


# ============================================================
# 🎭 الرتب
# ============================================================
ROLE_JAIL = {
    "id": None,
    "names": ["محجور", "المحجور", "المحجورين", "jail", "Jail", "Jailed"],
}

ROLE_TICKET = {
    "id": None,
    "names": ["مسؤول-التذاكر", "مسؤول التذاكر", "Support", "support", "الدعم"],
}

ROLE_APPLY = {
    "id": None,
    "names": ["مسؤول-التقديم", "مسؤول التقديم", "Applications", "تقديم"],
}


# ============================================================
# 📢 الرومات الإدارية
# ============================================================
CH_ADMIN_REVIEW = {
    "id": 1548492573813776435,
    "names": ["admin-review", "admin_review", "مراجعة-الادارة", "المراجعة"],
}

CH_JAIL = {
    "id": 1532133484129161347,
    "names": ["quarantine-zone", "quarantine_zone", "المحجورين", "الحجر", "jail"],
}


# ============================================================
# 💿 رومات اللوقات
# ============================================================
CH_LOG_DELETE = {
    "id": 1510246396169555978,
    "names": ["لوق_الحذف", "لوق-الحذف", "لوق الحذف"],
}

CH_LOG_JOIN_LEAVE = {
    "id": 1510246429908537424,
    "names": ["دخول_خروج", "دخول-خروج", "دخول وخروج"],
}

CH_LOG_BAN = {
    "id": 1510246461399634040,
    "names": ["لوق_طرد", "لوق-الطرد", "لوق الطرد"],
}

CH_LOG_ROLES = {
    "id": 1510246552256385124,
    "names": ["لوق_رتب", "لوق-الرتب", "لوق الرتب"],
}

CH_LOG_NICKNAME = {
    "idhere": 1510246582048653443):,
    "names": ["تغير_لقب", "**تغير-لقب", "ت غيرغيير اللقب"],
}

CH_LOG_TIMEOUT مس =مو {
    "id": None,
    "names": ["لوق_تايم", "لوق-تايم", "لوق التايم اوت"],
}

CH_LOG_NUKE = {
    "id": 1548492573813776435,
    "names": ["admin-review", "مراجعة-الادارة"],
}

CH_LOG_GUILD = {
    "id": 1548492573813776435,
    "names": ["admin-review", "مراجعة-الادارة"],
}


# ============================================================
# 🎫 رومات عامة
# ============================================================
CH_WELCOME = {
    "id": None,
    "names": ["الترحيب〢✋🏻", "الترحيب", "welcome", "Welcome"],
}

CH_ANNOUNCE = {
    "id": 1549470907834044436,
    "names": ["روم-الإعلانات", "الاعلانات", "الإعلانات", "announcements"],
}

# ⭐ محدّث
CH_TICKET_PANEL = {
    "id": 1548500331032354896,
    "names": ["الدعم-الفني🎫", "الدعم الفني", "support", "تذاكر"],
}

# ⭐ محدّث
CH_APPLY_PANEL = {
    "id": 1548500336543535224,
    "names": ["التقديم-للسيرفر", "التقديم", "apply", "تقديم"],
}

CH_TICKET_CATEGORY = {
    "id": None,
    "names": ["التذاكر", "Tickets", "tickets"],
}


# ============================================================
# 🛡️ رومات محمية إضافية
# ============================================================
PROTECTED_CHANNELS = [
    # 1234567890123456789,
]


# ============================================================
# 🛡️ Anti-Nuke
# ============================================================
ANTI_NUKE_ENABLED    = True
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


# ============================================================
# 📦 النسخ الاحتياطية
# ============================================================
BACKUP_ENABLED     = True
BACKUP_MAX_ICONS   = 5
BACKUP_MAX_BANNERS = 3

PERIODIC_BACKUP_ENABLED = True
PERIODIC_BACKUP_HOURS   = 1


# ============================================================
# ⏱️ Rate Limiting
# ============================================================
RATE_LIMITS = {
    "حجر":   {"max": 10, "window": 60},
    "طرد":   {"max": 5,  "window": 60},
    "تحذير": {"max": 15, "window": 60},
    "مسح":   {"max": 5,  "window": 60},
    "اعلان": {"max": 3,  "window": 60},
    "remind": {"max": 10, "window": 300},
}


# ============================================================
# 🤖 بوتات موثوقة
# ============================================================
TRUSTED_BOTS = []


# ============================================================
# 🎣 Anti-Phishing
# ============================================================
ANTI_PHISHING_ENABLED = True
ANTI_PHISHING_PUNISH = "ban"

PHISHING_DOMAINS = [
    "discord-nitro.com", "discordnitro.com", "discord-gift.com",
    "steamcommunlty.com", "steamcommunty.com", "steamcomrnunity.com",
    "stearncommunity.com", "free-nitro.com", "claim-nitro.com",
    "nitro-gift.com", "discord-app.com", "discord-apps.com",
    "discord-airdrop.com", "discordcrypto.com", "dlscord.com",
    "discordgift.site", "discordgift.xyz", "discord-gift.site",
    "twitch-gift.com", "twitchgift.com", "csgo-skins.com",
    "bit.ly/freenitro", "tinyurl.com/freenitro",
]

PHISHING_KEYWORDS = [
    "free nitro", "نيترو مجاني", "nitro free", "claim your nitro",
    "free-nitro", "steam gift", "هدية ستيم", "مجانا نيترو",
    "احصل على نيترو", "get free nitro",
]


# ============================================================
# 🛡️ Auto-Mod
# ============================================================
AUTOMOD_ENABLED = True

AUTOMOD_SETTINGS = {
    "max_emojis": 8,
    "emoji_action": "warn",

    "max_caps_percent": 0.7,
    "caps_min_length": 10,
    "caps_action": "delete_only",

    "max_mentions": 6,
    "mentions_action": "warn",

    "max_duplicates": 3,
    "duplicate_window": 5,
    "duplicate_action": "warn",

    "max_zalgo": 15,
    "zalgo_action": "delete_only",

    "max_symbols_percent": 0.5,
    "symbols_action": "delete_only",
}


# ============================================================
# 👋 Welcome Card
# ============================================================
WELCOME_CARD_ENABLED = True
WELCOME_CARD_BG_COLOR = (34, 40, 49)
WELCOME_CARD_ACCENT   = (114, 137, 218)
WELCOME_CARD_TITLE    = "WELCOME"
WELCOME_CARD_SUBTITLE = "Member #{count}"
WELCOME_CARD_SIZE     = (900, 300)


# ============================================================
# 📊 إحصائيات السيرفر
# ============================================================
STATS_ENABLED        = True
STATS_UPDATE_MINUTES = 10

# ⭐ آيدي روم الإحصائيات (يستخدم روم واحد يعرض الكل فيه)
CH_STATS = {
    "id": 1555459745752686653,
    "names": ["📊 Server Stats", "Server Stats", "الإحصائيات", "stats"],
}


# ============================================================
# 💬 نصوص ثابتة
# ============================================================
RULES_TEXT = """📜 **قوانين وعقوبات السيرفر:**

1. **السب والشتم والألفاظ النابية:** يمنع منعاً باتاً (العقوبة: حجر فوري مباشر 🔒).
2. **إرسال الروابط والدعوات الخارجية:** غير مسموح (العقوبة: تحذير + تايم آوت ساعة ⏱️).
3. **السبام وتكرار الرسائل:** غير مسموح (العقوبة: تحذير + تايم آوت ساعة ⏱️).
4. **منشن الجميع (@everyone / @ح (العقوبة: تحذير + تايم آوت ساعة ⏱️).
5. **الاحترام المتبادل:** يرجى احترام جميع الأعضاء لتجنب العقوبات.

⚠️ **تنبيه:** عند وصول العضو إلى **3 تحذيرات** يتم تحويله تلقائياً إلى الحجر!"""


# ============================================================
# 🚫 الكلمات المحظورة
# ============================================================
BAD_WORDS = [
    "كلب", "حمار", "قحبة", "قحبه", "شرموط", "شرطوط", "منيوك",
    "ديوث", "عرص", "خرا", "زق", "طيز", "زب", "سكس", "مخصي",
    "fuck", "shit", "bitch", "asshole", "dick", "cunt", "bastard",
    "slut", "whore", "pussy", "stfu", "motherfucker", "nigger",
]
# ============================================================
# 👋 Welcome Card
# ============================================================

def _wrap_text(text: str, max_chars: int = 20) -> str:
    """يقص النص لو طويل"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 1] + "…"


async def make_welcome_card(member: discord.Member) -> Optional[io.BytesIO]:
    """
    ينشئ صورة ترحيب بالأفاتار والاسم.
    يرجع BytesIO أو None إذا فشل.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
    except ImportError:
        log.warning("Pillow غير مثبتة — Welcome Card معطّل")
        return None

    try:
        width, height = config.WELCOME_CARD_SIZE
        bg_color = config.WELCOME_CARD_BG_COLOR
        accent = config.WELCOME_CARD_ACCENT

        # إنشاء الصورة
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # دائرة ملوّنة على اليسار
        circle_x = 150
        circle_y = height // 2
        circle_r = 100

        # دائرة خلفية الأفاتار
        draw.ellipse(
            [circle_x - circle_r - 5, circle_y - circle_r - 5,
             circle_x + circle_r + 5, circle_y + circle_r + 5],
            fill=accent
        )

        # تحميل الأفاتار
        avatar_bytes = await member.display_avatar.replace(
            size=256, format="png"
        ).read()

        avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
        avatar_img = avatar_img.resize((circle_r * 2, circle_r * 2), Image.LANCZOS)

        # قناع دائري
        mask = Image.new("L", (circle_r * 2, circle_r * 2), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, circle_r * 2, circle_r * 2], fill=255)

        # لصق الأفاتار
        img.paste(avatar_img, (circle_x - circle_r, circle_y - circle_r), mask)

        # محاولة تحميل خط عربي أو افتراضي
        font_big = None
        font_med = None
        font_small = None

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
        ]

        for path in font_paths:
            if os.path.exists(path):
                try:
                    font_big = ImageFont.truetype(path, 56)
                    font_med = ImageFont.truetype(path, 36)
                    font_small = ImageFont.truetype(path, 24)
                    break
                except Exception:
                    continue

        if font_big is None:
            font_big = ImageFont.load_default()
            font_med = font_big
            font_small = font_big

        # كتابة الاسم
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
            config.WELCOME_CARD_SUBTITLE.format(
                count=f"#{member.guild.member_count}"
            ),
            fill=(180, 180, 180),
            font=font_small,
        )

        # خط أسفل
        draw.rectangle(
            [text_x, height // 2 + 90, width - 60, height // 2 + 93],
            fill=accent,
        )

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

    except Exception as e:
        log.exception(f"فشل إنشاء Welcome Card: {e}")
        return None


# ============================================================
# 📊 إحصائيات السيرفر (تحديث روم واحد بالاسم)
# ============================================================

_last_stats_update = 0.0


async def update_guild_stats(guild: discord.Guild):
    """يحدّث اسم روم الإحصائيات"""
    global _last_stats_update
    if not config.STATS_ENABLED:
        return

    # تحديث كل X دقائق فقط (Discord rate limits)
    now = time.time()
    if now - _last_stats_update < 60:  # لا تحدّث أكثر من مرة بالدقيقة
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

    # حساب الإحصائيات
    total = guild.member_count
    bots = sum(1 for m in guild.members if m.bot)
    humans = total - bots
    channels_count = len(guild.channels)
    roles_count = len(guild.roles)

    # اسم الروم
    new_name = (
        f"📊 Members: {total:,} | "
        f"👥 Humans: {humans:,} | "
        f"🤖 Bots: {bots:,} | "
        f"💬 Channels: {channels_count} | "
        f"👑 Roles: {roles_count}"
    )

    # Discord max 100 characters
    if len(new_name) > 100:
        new_name = f"📊 Members: {total:,} | 👥 {humans:,} | 🤖 {bots:,}"

    try:
        if ch.name != new_name:
            await ch.edit(name=new_name, reason="تحديث الإحصائيات")
    except discord.Forbidden:
        log.warning("لا أملك صلاحية تعديل اسم روم الإحصائيات")
    except Exception as e:
        log.warning(f"فشل تحديث الإحصائيات: {e}")


# ============================================================
# 💾 نسخ احتياطية دورية
# ============================================================

async def periodic_backup_loop(bot: commands.Bot):
    """ينشئ نسخة احتياطية كل X ساعات"""
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
                    log.info(f"💾 نسخة احتياطية دورية: {guild.name}")
                except Exception as e:
                    log.warning(f"فشل النسخ الاحتياطي لـ {guild.name}: {e}")
        except Exception as e:
            log.exception(f"خطأ في periodic_backup_loop: {e}")


# ============================================================
# 🎯 الأوامر
# ============================================================

def setup_commands(bot: commands.Bot):
    """يسجل كل الأوامر"""

    # ---------- تذكيرات ----------
    @bot.tree.command(name="remind", description="ضع تذكيراً بعد مدة محددة")
    @app_commands.describe(
        duration="المدة (مثل: 10m / 2h / 1d / 1h30m)",
        text="نص التذكير",
    )
    async def remind_cmd(interaction: discord.Interaction,
                         duration: str, text: str):
        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message(
                "❌ صيغة المدة غير صحيحة. أمثلة: `10m`, `2h`, `1d`, `1h30m`",
                ephemeral=True,
            )
            return

        if seconds > 30 * 86400:  # 30 يوم
            await interaction.response.send_message(
                "❌ الحد الأقصى 30 يوم.", ephemeral=True
            )
            return

        # Rate limit
        check_rl = SHARED.get("check_rate_limit")
        if check_rl:
            ok, wait = check_rl(interaction.user.id, "remind")
            if not ok:
                await interaction.response.send_message(
                    f"⏱️ تجاوزت الحد. انتظر {wait} ثانية.", ephemeral=True
                )
                return

        due_time = time.time() + seconds
        reminder = {
            "user_id": interaction.user.id,
            "channel_id": interaction.channel_id,
            "text": text,
            "due": due_time,
            "original_link": interaction.channel.jump_url if hasattr(
                interaction.channel, "jump_url") else None,
        }
        REMINDERS.append(reminder)
        save_reminders()

        await interaction.response.send_message(
            f"✅ سأذكّرك بعد **{format_duration(seconds)}**.",
            ephemeral=True,
        )

    # ---------- Temp Ban ----------
    @bot.tree.command(name="tempban",
                      description="حظر مؤقت مع فك تلقائي")
    @app_commands.describe(
        member="العضو",
        duration="المدة (مثل: 1h / 1d / 7d)",
        reason="السبب",
    )
    async def tempban_cmd(interaction: discord.Interaction,
                          member: discord.Member,
                          duration: str,
                          reason: str = "لم يُحدد"):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message(
                "❌ صيغة غير صحيحة.", ephemeral=True
            )
            return

        if seconds > 30 * 86400:
            await interaction.response.send_message(
                "❌ الحد 30 يوم.", ephemeral=True
            )
            return

        # فحص ترتيب الرتب
        can_act = SHARED.get("can_act_on")
        if can_act:
            ok, why = can_act(interaction.user, member, interaction.guild)
            if not ok:
                await interaction.response.send_message(why, ephemeral=True)
                return

        try:
            # إرسال DM قبل الحظر
            try:
                await member.send(
                    f"🔨 **حظر مؤقت من {interaction.guild.name}**\n"
                    f"المدة: **{format_duration(seconds)}**\n"
                    f"السبب: {reason}"
                )
            except Exception:
                pass

            await member.ban(reason=f"TempBan ({format_duration(seconds)}) بواسطة {interaction.user}: {reason}",
                             delete_message_days=0)

            TEMP_ACTIONS.append({
                "guild_id": interaction.guild.id,
                "user_id": member.id,
                "type": "ban",
                "until": time.time() + seconds,
                "moderator": interaction.user.id,
                "reason": reason,
            })
            save_temp_actions()

            # لوق
            get_ch = SHARED.get("get_ch_admin_review")
            if get_ch:
                ch = get_ch(interaction.guild)
                if ch:
                    embed = discord.Embed(
                        title="🔨 حظر مؤقت",
                        color=discord.Color.dark_red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.add_field(name="العضو",
                                    value=f"{member} (`{member.id}`)",
                                    inline=False)
                    embed.add_field(name="بواسطة",
                                    value=interaction.user.mention,
                                    inline=False)
                    embed.add_field(name="المدة",
                                    value=format_duration(seconds),
                                    inline=True)
                    embed.add_field(name="السبب", value=reason, inline=False)
                    await ch.send(embed=embed)

            await interaction.response.send_message(
                f"✅ تم حظر {member.mention} لمدة **{format_duration(seconds)}**.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ فشل الحظر: {e}", ephemeral=True
            )

    # ---------- Temp Jail ----------
    @bot.tree.command(name="tempjail",
                      description="حجر مؤقت مع فك تلقائي")
    @app_commands.describe(
        member="العضو",
        duration="المدة (مثل: 1h / 1d)",
        reason="السبب",
    )
    async def tempjail_cmd(interaction: discord.Interaction,
                           member: discord.Member,
                           duration: str,
                           reason: str = "لم يُحدد"):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        seconds = parse_duration(duration)
        if not seconds:
            await interaction.response.send_message(
                "❌ صيغة غير صحيحة.", ephemeral=True
            )
            return

        if seconds > 30 * 86400:
            await interaction.response.send_message(
                "❌ الحد 30 يوم.", ephemeral=True
            )
            return

        apply_jail = SHARED.get("apply_jail")
        if not apply_jail:
            await interaction.response.send_message(
                "❌ خطأ داخلي.", ephemeral=True
            )
            return

        ok, msg = await apply_jail(
            interaction.guild, member,
            f"TempJail ({format_duration(seconds)}) بواسطة {interaction.user}: {reason}"
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
        save_temp_actions()

        # إشعار العضو
        try:
            await member.send(
                f"🔒 **حجر مؤقت من {interaction.guild.name}**\n"
                f"المدة: **{format_duration(seconds)}**\n"
                f"السبب: {reason}"
            )
        except Exception:
            pass

        # لوق
        get_ch = SHARED.get("get_ch_admin_review")
        if get_ch:
            ch = get_ch(interaction.guild)
            if ch:
                embed = discord.Embed(
                    title="🔒 حجر مؤقت",
                    color=discord.Color.dark_red(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(name="العضو",
                                value=f"{member.mention} (`{member.id}`)",
                                inline=False)
                embed.add_field(name="بواسطة",
                                value=interaction.user.mention,
                                inline=False)
                embed.add_field(name="المدة",
                                value=format_duration(seconds),
                                inline=True)
                embed.add_field(name="السبب", value=reason, inline=False)
                await ch.send(embed=embed)

        await interaction.response.send_message(
            f"✅ {msg}\nالمدة: **{format_duration(seconds)}**",
            ephemeral=True,
        )

    # ---------- قائمة العقوبات المؤقتة ----------
    @bot.tree.command(name="temp_list",
                      description="عرض العقوبات المؤقتة النشطة")
    async def temp_list_cmd(interaction: discord.Interaction):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        guild_actions = [a for a in TEMP_ACTIONS if a["guild_id"] == interaction.guild.id]

        if not guild_actions:
            await interaction.response.send_message(
                "ℹ️ لا توجد عقوبات مؤقتة نشطة.", ephemeral=True
            )
            return

        lines = []
        now = time.time()
        for a in guild_actions[:20]:
            remaining = int(a["until"] - now)
            kind = "🔨 حظر" if a["type"] == "ban" else "🔒 حجر"
            lines.append(
                f"{kind} — <@{a['user_id']}> — تبقى: **{format_duration(remaining)}**"
            )

        embed = discord.Embed(
            title="⏳ العقوبات المؤقتة",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------- إحصائيات (تحديث يدوي) ----------
    @bot.tree.command(name="تحديث_الاحصائيات",
                      description="تحديث روم الإحصائيات يدوياً")
    async def update_stats_cmd(interaction: discord.Interaction):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        global _last_stats_update
        _last_stats_update = 0  # تجاوز الـ cooldown

        await update_guild_stats(interaction.guild)
        await interaction.response.send_message(
            "✅ تم تحديث الإحصائيات.", ephemeral=True
        )

    # ---------- نسخة احتياطية يدوية ----------
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
                "✅ تم أخذ نسخة احتياطية كاملة.", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"❌ فشل: {e}", ephemeral=True)

    # ---------- فحص Auto-Mod ----------
    @bot.tree.command(name="اختبار_اوتو_مود",
                      description="اختبار فحص Auto-Mod على نص")
    @app_commands.describe(text="النص للفحص")
    async def automod_test_cmd(interaction: discord.Interaction, text: str):
        check_control = SHARED.get("require_control")
        if check_control and not await check_control(interaction):
            return

        # بناء كائن وهمي للفحص
        class FakeMessage:
            def __init__(self, content):
                self.content = content
                self.mentions = []

        result = automod_check(FakeMessage(text))
        if result:
            embed = discord.Embed(
                title="⚠️ Auto-Mod يكشف مخالفة",
                description=f"**السبب:** `{result['reason']}`\n"
                            f"**الإجراء:** `{result['action']}`\n"
                            f"**التفاصيل:** {result['detail']}",
                color=discord.Color.orange(),
            )
        else:
            embed = discord.Embed(
                title="✅ النص سليم",
                description="Auto-Mod لم يجد أي مخالفة.",
                color=discord.Color.green(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ---------- اختبار Anti-Phishing ----------
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
                title="🎣 رابط تصيّد مكتشف!",
                description=f"`{result}`",
                color=discord.Color.red(),
            )
        else:
            embed = discord.Embed(
                title="✅ الرابط سليم",
                color=discord.Color.green(),
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # ============================================================
# 🎣 Auto-Mod + Anti-Phishing — handler
# ============================================================

def setup_message_handler(bot: commands.Bot):
    """يُسجّل on_message جديد يشتغل قبل الموجود"""

    # حفظ المعالج القديم (لو موجود)
    old_handler = bot.on_message

    @bot.event
    async def on_message(message: discord.Message):
        # تجاهل
        if message.author.bot or not message.guild:
            if old_handler:
                await old_handler(message)
            return

        # فحص الاستثناءات
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

                # لوق قبل العقوبة
                get_ch = SHARED.get("get_ch_admin_review")
                log_ch = get_ch(guild) if get_ch else None

                punishment_msg = ""

                # عقوبة: بان أو حجر
                if config.ANTI_PHISHING_PUNISH == "ban":
                    try:
                        try:
                            await member.send(
                                f"🚫 **تم حظرك من {guild.name}**\n"
                                f"السبب: نشر رابط تصيّد (Phishing)"
                            )
                        except Exception:
                            pass

                        await member.ban(
                            reason=f"Anti-Phishing: {phishing_url}",
                            delete_message_days=3,
                        )
                        punishment_msg = "🔨 **حظر نهائي**"
                    except Exception as e:
                        punishment_msg = f"❌ فشل البان: {e}"

                elif config.ANTI_PHISHING_PUNISH == "jail":
                    apply_jail = SHARED.get("apply_jail")
                    if apply_jail:
                        ok, msg = await apply_jail(
                            guild, member,
                            f"Anti-Phishing: {phishing_url}"
                        )
                        punishment_msg = msg

                # لوق
                if log_ch:
                    embed = discord.Embed(
                        title="🎣 Anti-Phishing: تم كشف رابط تصيّد",
                        color=discord.Color.dark_red(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.set_author(
                        name=str(member),
                        icon_url=member.display_avatar.url,
                    )
                    embed.add_field(
                        name="العضو",
                        value=f"{member.mention} (`{member.id}`)",
                        inline=False,
                    )
                    embed.add_field(
                        name="الرابط المشبوه",
                        value=f"`{phishing_url}`",
                        inline=False,
                    )
                    embed.add_field(
                        name="الرسالة",
                        value=f"`{(message.content or '')[:500]}`",
                        inline=False,
                    )
                    embed.add_field(
                        name="العقوبة",
                        value=punishment_msg,
                        inline=False,
                    )
                    try:
                        await log_ch.send(embed=embed)
                    except Exception:
                        pass

                log.warning(f"🎣 Phishing detected: {member} → {phishing_url}")
                return  # لا تكمل

        # ---------- Auto-Mod ----------
        if config.AUTOMOD_ENABLED:
            result = automod_check(message)
            if result:
                try:
                    await message.delete()
                except Exception:
                    pass

                reason = result["reason"]
                action = result["action"]
                detail = result["detail"]

                action_taken = "🗑️ حذف الرسالة"

                if action == "warn":
                    # إضافة تحذير للنظام
                    USER_WARNINGS = SHARED.get("USER_WARNINGS")
                    save_warnings = SHARED.get("save_warnings")

                    if USER_WARNINGS is not None:
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        USER_WARNINGS.setdefault(member.id, []).append({
                            "reason": f"Auto-Mod: {reason} ({detail})",
                            "warned_by": "Auto-Mod 🤖",
                            "date": now_str,
                        })
                        if save_warnings:
                            await save_warnings()
                        warn_count = len(USER_WARNINGS[member.id])
                        action_taken = f"⚠️ تحذير رقم {warn_count}"

                        # 3 تحذيرات = حجر
                        if warn_count >= 3:
                            apply_jail = SHARED.get("apply_jail")
                            if apply_jail:
                                ok, msg = await apply_jail(
                                    guild, member,
                                    f"Auto-Mod: بلوغ {warn_count} تحذيرات"
                                )
                                action_taken += f"\n{msg}"

                    # إشعار بالخاص
                    try:
                        await member.send(
                            f"⚠️ **تنبيه Auto-Mod من {guild.name}**\n"
                            f"السبب: {reason} ({detail})\n"
                            f"الإجراء: {action_taken}"
                        )
                    except Exception:
                        pass

                elif action == "timeout":
                    try:
                        until = discord.utils.utcnow() + datetime.timedelta(minutes=10)
                        await member.timeout(
                            until,
                            reason=f"Auto-Mod: {reason} ({detail})"
                        )
                        action_taken = "⏱️ تايم آوت 10 دقائق"
                    except Exception as e:
                        action_taken = f"❌ فشل التايم آوت: {e}"

                elif action == "delete_only":
                    action له_taken الد = "🗑️ حذف الرسالة فقطوال"

                # لوق
                get_ch = المش SHARED.get("get_ch_admin_review")
                log_ch = get_ch(guild) if get_ch else None
                if log_ch:
                    embed = discord.Embed(
                        title="🛡️ Auto-Mod: مخالفة تلقائية",
                        color=discord.Color.orange(),
                        timestamp=discord.utils.utcnow(),
                    )
                    embed.set_author(
                        name=str(member),
                        icon_url=member.display_avatar.url,
                    )
                    embed.add_field(
                        name="العضو",
                        value=f"{member.mention} (`{member.id}`)",
                        inline=False,
                    )
                    embed.add_field(
                        name="الروم",
                        value=message.channel.mention,
                        inline=True,
                    )
                    embed.add_field(
                        name="النوع",
                        value=f"`{reason}`",
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
                        value=f"`{content}`",
                        inline=False,
                    )
                    try:
                        await log_ch.send(embed=embed)
                    except Exception:
                        pass

                log.info(f"🛡️ Auto-Mod: {member} → {reason} ({action_taken})")
                return  # لا تكمل للأمر القديم

        # مرّر الرسالة للمعالج القديم (لو موجود)
        if old_handler:
            await old_handler(message)


# ============================================================
# 🚀 load_extras — الدالة الرئيسية
# ============================================================

def load_extras(bot: commands.Bot, shared: dict):
    """
    يُحمّل كل الإضافات.
    - bot: كائن البوت
    - shared: قاموس يحتوي الدوال والكائنات المشتركة من main.py
    """
    # اربط SHARED
    SHARED.clear()
    SHARED.update(shared)

    # تحميل الملفات
    load_reminders()
    load_temp_actions()

    # تسجيل الأوامر
    setup_commands(bot)

    # تسجيل معالج الرسائل
    setup_message_handler(bot)

    # تسجيل on_member_join للـ Welcome Card
    old_on_join = bot.on_member_join if hasattr(bot, "on_member_join") else None

    async def welcome_card_handler(member: discord.Member):
        """يُرسل Welcome Card في روم الترحيب"""

        # تشغيل المعالج القديم
        if old_on_join:
            try:
                await old_on_join(member)
            except Exception as e:
                log.warning(f"فشل المعالج القديم في on_member_join: {e}")

        if not config.WELCOME_CARD_ENABLED:
            return

        get_ch_welcome = SHARED.get("get_ch_welcome")
        if not get_ch_welcome:
            return

        ch = get_ch_welcome(member.guild)
        if not ch:
            return

        # إنشاء الصورة
        card = await make_welcome_card(member)
        if card:
            try:
                await ch.send(
                    content=f"Welcome {member.mention}! 🎉",
                    file=discord.File(card, filename="welcome.png"),
                )
                return
            except Exception as e:
                log.warning(f"فشل إرسال Welcome Card: {e}")

        # لو الصورة فشلت — نرسل embed عادي
        embed = discord.Embed(
            title="🎉 عضو جديد!",
            description=f"مرحباً {member.mention} في **{member.guild.name}**!",
            color=discord.Color.brand_green(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await ch.send(content=member.mention, embed=embed)
        except Exception:
            pass

    # إعادة تسجيل الحدث
    bot.remove_listener(welcome_card_handler, "on_member_join")  # احتياط
    bot.add_listener(welcome_card_handler, "on_member_join")

    # ---- تشغيل المهام الدورية كـ tasks ----
    bot.loop.create_task(reminder_loop(bot))
    bot.loop.create_task(temp_actions_loop(bot))

    if config.PERIODIC_BACKUP_ENABLED:
        bot.loop.create_task(periodic_backup_loop(bot))

    # ---- تحديث الإحصائيات عند البدء وكل X دقيقة ----
    async def stats_loop():
        await bot.wait_until_ready()
        while True:
            try:
                for guild in bot.guilds:
                    await update_guild_stats(guild)
            except Exception as e:
                log.warning(f"خطأ في stats_loop: {e}")
            await asyncio.sleep(config.STATS_UPDATE_MINUTES * 60)

    bot.loop.create_task(stats_loop())

    log.info("✅ تم تحميل extras.py — كل الإضافات شغالة")
