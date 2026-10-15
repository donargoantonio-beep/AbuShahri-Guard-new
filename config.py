"""
config.py — الإصدار 7.1
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
# رابط الاتصال بقاعدة البيانات (يُقرأ من Render Environment)
MONGO_URI = os.getenv("MONGO_URI", "")

# اسم قاعدة البيانات
MONGO_DB_NAME = "abushahri_guard"

# حالة تفعيل MongoDB (تتغير تلقائياً حسب الاتصال)
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

# ملفات البيانات (تُنشأ تلقائياً)
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

# روم التوقيف (المتوقفين يقعدون فيه)
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

# 🤖 لوق العقوبات التلقائية (سب، Auto-Mod، Anti-Phishing، Anti-Nuke)
# ملاحظة: نفس روم admin-review
CH_LOG_AUTO = {
    "id": 1548492573813776435,
    "names": ["admin-review"],
}

# 🔧 لوق التعديلات (رسائل، رتب، ألقاب، رومات)
# ملاحظة: نفس روم لوق_رتب
CH_LOG_CHANGES = {
    "id": 1510246552256385124,
    "names": ["لوق_التعديلات", "لوق_رتب"],
}

# 📜 لوق البرقيات والتقديم
# ملاحظة: نفس روم admin-review
CH_LOG_TICKETS = {
    "id": 1548492573813776435,
    "names": ["admin-review"],
}

# 📤 لوق الخروج فقط
CH_LOG_LEAVE = {
    "id": 1510246429908537424,
    "names": ["لوق_الخروج"],
}

# ─── توافق مع الكود (كل لوق يروح للروم المناسب) ───
CH_LOG_DELETE     = CH_LOG_CHANGES    # حذف الرسائل → التعديلات
CH_LOG_JOIN_LEAVE = CH_LOG_LEAVE      # دخول/خروج → لوق الخروج
CH_LOG_BAN        = CH_LOG_MANUAL     # باند → العقوبات اليدوية
CH_LOG_ROLES      = CH_LOG_CHANGES    # رتب → التعديلات
CH_LOG_NICKNAME   = CH_LOG_CHANGES    # ألقاب → التعديلات
CH_LOG_TIMEOUT    = CH_LOG_MANUAL     # تايم → العقوبات اليدوية
CH_LOG_NUKE       = CH_LOG_AUTO       # نيوك → العقوبات التلقائية
CH_LOG_GUILD      = CH_LOG_AUTO       # حماية السيرفر → التلقائية
CH_LOG_CHANNEL    = CH_LOG_CHANGES    # رومات → التعديلات
CH_LOG_JAIL       = CH_LOG_MANUAL     # توقيف → العقوبات اليدوية


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

# 📜 روم بانل البرقيات (الزر يظهر هنا)
CH_TICKET_PANEL = {
    "id": 1548500331032354896,
    "names": ["البرقيات", "الدعم-الفني", "support"],
}

# 🇸🇦 روم بانل الجنسية (الزر يظهر هنا)
CH_APPLY_PANEL = {
    "id": 1548500336543535224,
    "names": ["التقديم-للسيرفر", "التقديم", "الجنسية"],
}

# 🎫 تصنيف البرقيات (تُفتح فيه رومات البرقيات)
CH_TICKET_CATEGORY = {
    "id": None,
    "names": ["البرقيات", "التذاكر", "Tickets", "tickets"],
}

# 📊 روم الإحصائيات (يتحدث تلقائياً)
CH_STATS = {
    "id": 1555459745752686653,
    "names": ["Server Stats", "الإحصائيات", "stats"],
}


# ============================================================
# 🛡️ رومات محمية إضافية
# ============================================================
# أضف آيديات الرومات اللي تبي تحميها بالقوة
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

# نظام العقوبة التدريجية (بدون تحذير):
#   أول نيك  → حجر مؤقت 24 ساعة
#   ثاني نيك → حجر دائم
#   ثالث +   → حجر دائم
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
    # منشنات
    "max_mentions": 6,
    "mentions_action": "warn",

    # رسائل مكررة (سبام)
    "max_duplicates": 3,
    "duplicate_window": 5,
    "duplicate_action": "warn",

    # Zalgo (رموز مشوهة)
    "max_zalgo": 15,
    "zalgo_action": "delete_only",

    # رموز (!@#$%...)
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
# 📊 إحصائيات السيرفر
# ============================================================
STATS_ENABLED        = True
STATS_UPDATE_MINUTES = 10


# ============================================================
# 📬 إشعار الرتب
# ============================================================
# إرسال DM للعضو عند إعطائه رتبة
ROLE_NOTIFY_ENABLED = True

# تجاهل هذه الرتب (ما نرسل DM عند إعطائها)
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
# البوت يستخدم regex بحدود دقيقة
# لن يمنع كلمات مثل "مكسور" بسبب وجود "كس" داخلها
BAD_WORDS = [
    # عربي
    "كلب", "حمار", "قحبة", "قحبه", "شرموط", "شرطوط", "منيوك",
    "ديوث", "عرص", "خرا", "زق", "طيز", "زب", "سكس", "مخصي",

    # English
    "fuck", "shit", "bitch", "asshole", "dick", "cunt", "bastard",
    "slut", "whore", "pussy", "stfu", "motherfucker", "nigger",
]
