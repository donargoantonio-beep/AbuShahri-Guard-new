"""
config.py — الإصدار 7.2
كل إعدادات المملكة في مكان واحد
"""

import os

# ============================================================
# 👑 مالك البوت
# ============================================================
BOT_OWNER_ID = 813236200142929950


# ============================================================
# 🗄️ MongoDB (قاعدة البيانات الدائمة)
# ============================================================
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = "abushahri_guard"
MONGO_ENABLED = bool(MONGO_URI)


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
BOT_LOG_FILE       = "logs/bot.log"


# ============================================================
# 🎭 الرتب
# ============================================================
# كل رتبة لها:
#   id    = آيدي الرتبة (الأدق — اتركه None للبحث بالاسم)
#   names = قائمة أسماء بديلة (أي واحد يطابق يكفي)
# ============================================================

# 🇸🇦 رتبة المواطنة (تُعطى عند قبول الجنسية)
CITIZEN_ROLE = {
    "id": None,
    "names": ["🇸🇦〢سعودي", "سعودي", "مواطن", "Citizen"],
}

# 🚔 رتبة التوقيف (بدل "محجور" سابقاً)
ROLE_JAIL = {
    "id": None,
    "names": ["🚔〢متوقف", "متوقف", "المتوقف", "الموقوف", "محجور", "jail"],
}

# 👨🏻‍✈️ رتبة وزير الداخلية (يقبل/يرفض/يغلق البرقيات والجنسية)
ROLE_MINISTER = {
    "id": None,
    "names": [
        "👨🏻‍✈️〢وزير-الداخلية",
        "وزير-الداخلية",
        "وزير الداخلية",
        "وزيرالداخلية",
    ],
}

ROLE_TICKET = {
    "id": None,
    "names": ["مسؤول-التذاكر", "مسؤول التذاكر", "Support", "support", "الدعم", "مسؤول-البرقيات"],
}

ROLE_APPLY = {
    "id": None,
    "names": ["مسؤول-التقديم", "مسؤول التقديم", "Applications", "تقديم", "مسؤول-الجنسية"],
}


# ============================================================
# 📢 الرومات الإدارية
# ============================================================

# روم مراجعة الإدارة (برقيات + تقديمات + تقارير)
CH_ADMIN_REVIEW = {
    "id": 1548492573813776435,
    "names": ["admin-review", "admin_review", "مراجعة-الادارة"],
}

# روم التوقيف
CH_JAIL = {
    "id": 1532133484129161347,
    "names": ["quarantine-zone", "quarantine_zone", "المتوقفين", "التوقيف", "jail"],
}


# ============================================================
# 💿 رومات اللوقات
# ============================================================

# 👮 لوق العقوبات اليدوية (تايم، توقيف، باند، طرد يدوي)
CH_LOG_MANUAL = {
    "id": 1560281673046818926,
    "names": ["لوق_العقوبات_اليدوية", "العقوبات-اليدوية"],
}

# 🤖 لوق العقوبات التلقائية = admin-review
CH_LOG_AUTO = {
    "id": 1548492573813776435,
    "names": ["admin-review"],
}

# 🔧 لوق التعديلات (رسائل، رتب، ألقاب، رومات) = لوق_رتب
CH_LOG_CHANGES = {
    "id": 1510246552256385124,
    "names": ["لوق_التعديلات", "لوق_رتب"],
}

# 📜 لوق البرقيات والتقديم = admin-review
CH_LOG_TICKETS = {
    "id": 1548492573813776435,
    "names": ["admin-review"],
}

# 📤 لوق الخروج فقط
CH_LOG_LEAVE = {
    "id": 1510246429908537424,
    "names": ["لوق_الخروج"],
}

# ─── توافق مع الكود ───
CH_LOG_DELETE     = CH_LOG_CHANGES
CH_LOG_JOIN_LEAVE = CH_LOG_LEAVE
CH_LOG_BAN        = CH_LOG_MANUAL
CH_LOG_ROLES      = CH_LOG_CHANGES
CH_LOG_NICKNAME   = CH_LOG_CHANGES
CH_LOG_TIMEOUT    = CH_LOG_MANUAL
CH_LOG_NUKE       = CH_LOG_AUTO
CH_LOG_GUILD      = CH_LOG_AUTO
CH_LOG_CHANNEL    = CH_LOG_CHANGES
CH_LOG_JAIL       = CH_LOG_MANUAL


# ============================================================
# 🎫 الرومات العامة
# ============================================================

# 👋 روم الترحيب
CH_WELCOME = {
    "id": 1549343919203033118,
    "names": ["الترحيب〢✋🏻", "الترحيب", "welcome"],
}

# 📢 روم الإعلانات
CH_ANNOUNCE = {
    "id": 1549470907834044436,
    "names": ["روم-الإعلانات", "الاعلانات", "الإعلانات"],
}

# 📜 روم بانل البرقيات
CH_TICKET_PANEL = {
    "id": 1548500331032354896,
    "names": ["البرقيات", "الدعم-الفني", "support"],
}

# 🇸🇦 روم بانل الجنسية
CH_APPLY_PANEL = {
    "id": 1548500336543535224,
    "names": ["التقديم-للسيرفر", "التقديم", "الجنسية"],
}

# 🎫 تصنيف البرقيات
CH_TICKET_CATEGORY = {
    "id": None,
    "names": ["البرقيات", "التذاكر", "Tickets", "tickets"],
}


# ============================================================
# 🛡️ رومات محمية إضافية
# ============================================================
PROTECTED_CHANNELS = []


# ============================================================
# 🛡️ Anti-Nuke
# ============================================================
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
    "أمر_توقيف":  {"max": 10, "window": 60},
    "إنذار_رسمي": {"max": 15, "window": 60},
    "تنظيف":      {"max": 5,  "window": 60},
    "بيان_رسمي":  {"max": 3,  "window": 60},
    "تذكير":      {"max": 10, "window": 300},
}


# ============================================================
# 🎣 Anti-Phishing
# ============================================================
ANTI_PHISHING_ENABLED = True
ANTI_PHISHING_PUNISH = "jail"

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
WELCOME_CARD_ENABLED  = True
WELCOME_CARD_BG_COLOR = (34, 40, 49)
WELCOME_CARD_ACCENT   = (0, 122, 61)
WELCOME_CARD_TITLE    = "WELCOME"
WELCOME_CARD_SUBTITLE = "Member #{count}"
WELCOME_CARD_SIZE     = (900, 300)


# ============================================================
# 📬 إشعار الرتب
# ============================================================
ROLE_NOTIFY_ENABLED = True
ROLE_NOTIFY_IGNORE = ["🚔〢متوقف", "متوقف", "محجور", "Muted"]


# ============================================================
# 💬 نصوص ثابتة
# ============================================================
RULES_TEXT = """📜 قوانين وعقوبات السيرفر:

1. السب والشتم والألفاظ النابية: يمنع منعاً باتاً (العقوبة: توقيف فوري مباشر 🚔).
2. إرسال الروابط والدعوات الخارجية: غير مسموح (العقوبة: إنذار + تايم آوت ساعة ⏱️).
3. السبام وتكرار الرسائل: غير مسموح (العقوبة: إنذار + تايم آوت ساعة ⏱️).
4. منشن الجميع (@everyone / @here): غير مسموح (العقوبة: إنذار + تايم آوت ساعة ⏱️).
5. الاحترام المتبادل: يرجى احترام جميع الأعضاء لتجنب العقوبات.

⚠️ تنبيه: عند وصول العضو إلى 3 إنذارات يتم تحويله تلقائياً إلى التوقيف!"""


# ============================================================
# 🚫 الكلمات المحظورة
# ============================================================
BAD_WORDS = [
    "كلب", "حمار", "قحبة", "قحبه", "شرموط", "شرطوط", "منيوك",
    "ديوث", "عرص", "خرا", "زق", "طيز", "زب", "سكس", "مخصي",
    "fuck", "shit", "bitch", "asshole", "dick", "cunt", "bastard",
    "slut", "whore", "pussy", "stfu", "motherfucker", "nigger",
]
