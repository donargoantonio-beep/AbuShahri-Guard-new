import os

# 👑 مالك البوت
BOT_OWNER_ID = 813236200142929950

# 🗄️ MongoDB
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = "abushahri_guard"
MONGO_ENABLED = bool(MONGO_URI)

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
BACKUP_FILE = "data/backup_meta.json"
GUILD_CACHE_FILE = "data/guild_cache.json"
TEMP_ACTIONS_FILE = "data/temp_actions.json"
BOT_LOG_FILE = "logs/bot.log"

# 🎭 الرتب
CITIZEN_ROLE = {"id": None, "names": ["🇸🇦〢سعودي", "سعودي", "مواطن"]}
ROLE_JAIL = {"id": None, "names": ["🚔〢متوقف", "متوقف", "محجور"]}
ROLE_MINISTER = {"id": None, "names": ["👨🏻‍✈️〢وزير-الداخلية", "وزير-الداخلية", "وزير الداخلية"]}
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

# ─── توافق مع الكود ───
CH_LOG_DELETE = CH_LOG_CHANGES
CH_LOG_JOIN_LEAVE = CH_LOG_LEAVE
CH_LOG_BAN = CH_LOG_MANUAL
CH_LOG_ROLES = CH_LOG_CHANGES
CH_LOG_NICKNAME = CH_LOG_CHANGES
CH_LOG_TIMEOUT = CH_LOG_MANUAL
CH_LOG_NUKE = CH_LOG_AUTO
CH_LOG_GUILD = CH_LOG_AUTO
CH_LOG_CHANNEL = CH_LOG_CHANGES
CH_LOG_JAIL = CH_LOG_MANUAL

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

# 📦 النسخ الاحتياطية
BACKUP_ENABLED = True
BACKUP_MAX_ICONS = 5
BACKUP_MAX_BANNERS = 3

# ⏱️ Rate Limiting
RATE_LIMITS = {
    "أمر_توقيف": {"max": 10, "window": 60},
    "إنذار_رسمي": {"max": 15, "window": 60},
    "تنظيف": {"max": 5, "window": 60},
    "بيان_رسمي": {"max": 3, "window": 60},
    "تذكير": {"max": 10, "window": 300},
}

# 🛡️ Auto-Mod
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

BAD_WORDS = ["كلب", "حمار", "قحبة", "شرموط", "fuck", "shit", "bitch"]
