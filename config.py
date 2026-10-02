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
