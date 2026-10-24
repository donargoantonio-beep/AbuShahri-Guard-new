# ═══════════════════════════════════════════════════════════════
# 📦 القسم 1: الاستيراد والمكتبات
# ═══════════════════════════════════════════════════════════════
import os
from dotenv import load_dotenv
load_dotenv()
import re
import json
import time
import shutil
import asyncio
import logging
import datetime
from collections import defaultdict, deque
from typing import Optional, Union

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

import config

try:
    with open("token.txt", "r", encoding="utf-8") as f:
        TOKEN = f.read().strip()
except FileNotFoundError:
TOKEN = os.getenv("DISCORD_TOKEN")

# ═══════════════════════════════════════════════════════════════
# ⚙️ القسم 2: إعداد البوت والنوايا
# ═══════════════════════════════════════════════════════════════

os.makedirs(config.LOGS_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(config.BOT_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("bot")

for d in [config.DATA_DIR, config.BACKUPS_DIR,
          config.ICONS_DIR, config.BANNERS_DIR, config.LOGS_DIR,
          config.CARDS_DIR]:
    os.makedirs(d, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!nobotprefix!",
    intents=intents,
    help_command=None,
)

# ═══════════════════════════════════════════════════════════════
# 💾 القسم 3: الحالة العامة
# ═══════════════════════════════════════════════════════════════

VOICE_CHANNEL_ID: int = 0
USER_WARNINGS: dict = {}
saved_roles: dict = {}
protected_users_list: list = []
protected_roles_list: list = []
deputy_user_ids: list = []
trusted_bots: list = []
SPAM_TRACKER: dict = {}
SPAM_CLEANUP_LAST = 0.0

NUKE_TRACKER: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
NUKE_STRIKES: dict = defaultdict(lambda: defaultdict(int))
RATE_LIMIT_TRACKER: dict = defaultdict(lambda: defaultdict(deque))

# ═══════════════════════════════════════════════════════════════
# 💿 القسم 4: حفظ وقراءة (JSON + MongoDB)
# ═══════════════════════════════════════════════════════════════

def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("خطأ في قراءة %s: %s", path, e)
        return default

def _write_json(path: str, data) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        log.error("خطأ في حفظ %s: %s", path, e)

async def async_save_json(path: str, data) -> None:
    await asyncio.to_thread(_write_json, path, data)

# ─── MongoDB ───
_db = None
_collections = {}

async def init_mongodb() -> bool:
    global _db, _collections

    if not config.MONGO_ENABLED:
        log.warning("MongoDB غير مفعل -- سيتم استخدام ملفات JSON")
        return False

    try:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(
            config.MONGO_URI,
            serverSelectionTimeoutMS=10000
        )
        await client.admin.command("ping")
        _db = client[config.MONGO_DB_NAME]

        _collections = {
            "state": _db["state"],
            "warnings": _db["warnings"],
            "antinuke": _db["antinuke"],
            "reminders": _db["reminders"],
            "temp_actions": _db["temp_actions"],
            "guild_cache": _db["guild_cache"],
            "backup_meta": _db["backup_meta"],
            "settings": _db["settings"],
        }
        log.info("✅ تم الاتصال بـ MongoDB Atlas بنجاح")
        return True
    except Exception as e:
        log.error("❌ فشل الاتصال بـ MongoDB: %s", e)
        config.MONGO_ENABLED = False
        return False

async def mongo_read(name: str, default):
    if not config.MONGO_ENABLED or name not in _collections:
        return default
    try:
        doc = await _collections[name].find_one({"_id": "main"})
        if doc:
            doc.pop("_id", None)
            return doc
        return default
    except Exception as e:
        log.error("فشل قراءة %s من MongoDB: %s", name, e)
        return default

async def mongo_save(name: str, data):
    if not config.MONGO_ENABLED or name not in _collections:
        return
    try:
        await _collections[name].replace_one(
            {"_id": "main"},
            {"_id": "main", **data},
            upsert=True,
        )
    except Exception as e:
        log.error("فشل حفظ %s في MongoDB: %s", name, e)

# ─── دوال الحفظ الموحدة ───

async def save_warnings() -> None:
    data = {str(k): v for k, v in USER_WARNINGS.items()}
    if config.MONGO_ENABLED:
        await mongo_save("warnings", {"data": data})
    else:
        await async_save_json(config.WARNINGS_FILE, data)

async def save_state() -> None:
    data = {
        "protected_users": protected_users_list,
        "protected_roles": protected_roles_list,
        "deputies": deputy_user_ids,
        "trusted_bots": trusted_bots,
        "voice_channel_id": VOICE_CHANNEL_ID,
        "saved_roles": {str(k): v for k, v in saved_roles.items()},
    }
    if config.MONGO_ENABLED:
        await mongo_save("state", data)
    else:
        await async_save_json(config.STATE_FILE, data)

async def save_nuke_strikes() -> None:
    data = {str(gid): {str(uid): c for uid, c in users.items()}
            for gid, users in NUKE_STRIKES.items()}
    if config.MONGO_ENABLED:
        await mongo_save("antinuke", {"data": data})
    else:
        await async_save_json(config.ANTINUKE_FILE, data)

# ─── تحميل الحالة الكامل ───

async def load_all_state_async() -> None:
    global USER_WARNINGS, saved_roles, protected_users_list
    global protected_roles_list, deputy_user_ids, VOICE_CHANNEL_ID
    global trusted_bots, NUKE_STRIKES

    if config.MONGO_ENABLED:
        log.info("تحميل الحالة من MongoDB...")

        data = await mongo_read("warnings", {"data": {}})
        USER_WARNINGS = {int(k): v for k, v in data.get("data", {}).items()}

        state = await mongo_read("state", {})
        protected_users_list = state.get("protected_users", [])
        protected_roles_list = state.get("protected_roles", [])
        deputy_user_ids = state.get("deputies", [])
        trusted_bots = state.get("trusted_bots", [])
        VOICE_CHANNEL_ID = state.get("voice_channel_id", 0)
        saved_roles = {int(k): v for k, v in state.get("saved_roles", {}).items()}

        strikes = await mongo_read("antinuke", {"data": {}})
        NUKE_STRIKES = defaultdict(lambda: defaultdict(int))
        for gid, users in strikes.get("data", {}).items():
            for uid, count in users.items():
                NUKE_STRIKES[int(gid)][int(uid)] = count

        log.info("✅ تم تحميل الحالة من MongoDB")
    else:
        log.info("تحميل الحالة من ملفات JSON...")

        raw = _read_json(config.WARNINGS_FILE, {})
        USER_WARNINGS = {int(k): v for k, v in raw.items()}

        state = _read_json(config.STATE_FILE, {})
        protected_users_list = state.get("protected_users", [])
        protected_roles_list = state.get("protected_roles", [])
        deputy_user_ids = state.get("deputies", [])
        trusted_bots = state.get("trusted_bots", [])
        VOICE_CHANNEL_ID = state.get("voice_channel_id", 0)
        saved_roles = {int(k): v for k, v in state.get("saved_roles", {}).items()}

        strikes = _read_json(config.ANTINUKE_FILE, {})
        NUKE_STRIKES = defaultdict(lambda: defaultdict(int))
        for gid, users in strikes.items():
            for uid, count in users.items():
                NUKE_STRIKES[int(gid)][int(uid)] = count

    log.info(
        "الحالة | تحذيرات=%d | محميون=%d | رتب-محمية=%d | نواب=%d | بوتات=%d",
        len(USER_WARNINGS), len(protected_users_list),
        len(protected_roles_list), len(deputy_user_ids), len(trusted_bots),
    )

# ═══════════════════════════════════════════════════════════════
# 🔍 القسم 5: البحث الذكي
# ═══════════════════════════════════════════════════════════════

def find_role(guild: discord.Guild, cfg: dict) -> Optional[discord.Role]:
    if cfg.get("id"):
        role = guild.get_role(cfg["id"])
        if role:
            return role

    for name in cfg["names"]:
        role = discord.utils.get(guild.roles, name=name)
        if role:
            return role

    names_lower = [n.lower() for n in cfg["names"]]
    for role in guild.roles:
        if role.name.lower() in names_lower:
            return role

    return None

def find_channel(guild: discord.Guild, cfg: dict,
                 channel_type: str = "text") -> Optional[discord.abc.GuildChannel]:
    if cfg.get("id"):
        ch = guild.get_channel(cfg["id"])
        if ch:
            if channel_type == "text" and isinstance(ch, discord.TextChannel):
                return ch
            if channel_type == "voice" and isinstance(ch, discord.VoiceChannel):
                return ch
            if channel_type == "category" and isinstance(ch, discord.CategoryChannel):
                return ch

    if channel_type == "text":
        channels = guild.text_channels
    elif channel_type == "voice":
        channels = guild.voice_channels
    elif channel_type == "category":
        channels = guild.categories
    else:
        channels = guild.channels

    for name in cfg["names"]:
        for ch in channels:
            if ch.name == name:
                return ch

    for name in cfg["names"]:
        for ch in channels:
            if ch.name.startswith(name):
                return ch

    names_lower = [n.lower() for n in cfg["names"]]
    for ch in channels:
        ch_lower = ch.name.lower()
        for n in names_lower:
            if n in ch_lower:
                return ch

    return None

# ─── اختصارات ───

def get_role_jail(g):      return find_role(g, config.ROLE_JAIL)
def get_role_ticket(g):    return find_role(g, config.ROLE_TICKET)
def get_role_apply(g):     return find_role(g, config.ROLE_APPLY)
def get_role_citizen(g):   return find_role(g, config.CITIZEN_ROLE)
def get_role_minister(g):  return find_role(g, config.ROLE_MINISTER)

def get_ch_admin_review(g):   return find_channel(g, config.CH_ADMIN_REVIEW, "text")
def get_ch_jail(g):           return find_channel(g, config.CH_JAIL, "text")
def get_ch_log_manual(g):     return find_channel(g, config.CH_LOG_MANUAL, "text")
def get_ch_log_auto(g):       return find_channel(g, config.CH_LOG_AUTO, "text")
def get_ch_log_changes(g):    return find_channel(g, config.CH_LOG_CHANGES, "text")
def get_ch_log_tickets(g):    return find_channel(g, config.CH_LOG_TICKETS, "text")
def get_ch_log_leave(g):      return find_channel(g, config.CH_LOG_LEAVE, "text")
def get_ch_log_nuke(g):       return find_channel(g, config.CH_LOG_NUKE, "text")
def get_ch_log_guild(g):      return find_channel(g, config.CH_LOG_GUILD, "text")
def get_ch_log_delete(g):     return find_channel(g, config.CH_LOG_DELETE, "text")
def get_ch_log_join_leave(g): return find_channel(g, config.CH_LOG_JOIN_LEAVE, "text")
def get_ch_log_ban(g):        return find_channel(g, config.CH_LOG_BAN, "text")
def get_ch_log_roles(g):      return find_channel(g, config.CH_LOG_ROLES, "text")
def get_ch_log_nickname(g):   return find_channel(g, config.CH_LOG_NICKNAME, "text")
def get_ch_log_timeout(g):    return find_channel(g, config.CH_LOG_TIMEOUT, "text")
def get_ch_log_channel(g):    return find_channel(g, config.CH_LOG_CHANNEL, "text")
def get_ch_welcome(g):        return find_channel(g, config.CH_WELCOME, "text")
def get_ch_announce(g):       return find_channel(g, config.CH_ANNOUNCE, "text")
def get_ch_ticket_panel(g):   return find_channel(g, config.CH_TICKET_PANEL, "text")
def get_ch_apply_panel(g):    return find_channel(g, config.CH_APPLY_PANEL, "text")
def get_cat_ticket(g):        return find_channel(g, config.CH_TICKET_CATEGORY, "category")# ═══════════════════════════════════════════════════════════════
# ⚖️ القسم 7: فحص الرتب + Rate Limiting
# ═══════════════════════════════════════════════════════════════

def can_act_on(actor: discord.Member, target: discord.Member,
               guild: discord.Guild):
    me = guild.me

    if target.id == me.id:
        return False, "❌ لا أستطيع معاقبة نفسي."
    if target.id == guild.owner_id:
        return False, "❌ لا يمكن معاقبة مالك السيرفر."
    if is_exempted(target):
        return False, "🛡️ هذا العضو محمي من العقوبات."
    if target.top_role >= me.top_role:
        return False, "❌ رتبة " + target.mention + " أعلى أو تساوي رتبة البوت."

    if isinstance(actor, discord.Member) and actor.id != me.id:
        if not is_owner(actor.id) and not is_deputy(actor.id):
            if actor.guild and actor.id != actor.guild.owner_id:
                if target.top_role >= actor.top_role:
                    return False, "❌ لا تستطيع معاقبة عضو رتبته أعلى أو تساوي رتبتك."

    return True, ""

def bot_can_manage(target, guild: discord.Guild):
    me = guild.me

    if isinstance(target, discord.Member):
        if target.id == guild.owner_id:
            return False, "لا أستطيع تعديل مالك السيرفر"
        if target.top_role >= me.top_role:
            return False, "رتبته أعلى أو تساوي رتبة البوت"

    if isinstance(target, discord.Role):
        if target.is_default():
            return False, "لا يمكن تعديل @everyone"
        if target >= me.top_role:
            return False, "الرتبة أعلى أو تساوي رتبة البوت"

    return True, ""

def check_rate_limit(user_id: int, command: str):
    if command not in config.RATE_LIMITS:
        return True, 0

    limit = config.RATE_LIMITS[command]
    max_calls = limit["max"]
    window = limit["window"]

    now = time.time()
    dq = RATE_LIMIT_TRACKER[user_id][command]

    while dq and now - dq[0] > window:
        dq.popleft()

    if len(dq) >= max_calls:
        wait = int(window - (now - dq[0])) + 1
        return False, wait

    dq.append(now)
    return True, 0

def cleanup_spam_tracker():
    global SPAM_CLEANUP_LAST
    now = time.time()
    if now - SPAM_CLEANUP_LAST < 300:
        return
    SPAM_CLEANUP_LAST = now
    cutoff = now - 60
    for uid in list(SPAM_TRACKER.keys()):
        if SPAM_TRACKER[uid][1] < cutoff:
            del SPAM_TRACKER[uid]

# ═══════════════════════════════════════════════════════════════
# 🧹 القسم 8: تطبيع النص والكلمات المحظورة
# ═══════════════════════════════════════════════════════════════

_TASHKEEL_RE = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
_LEET_MAP = str.maketrans({
    '@': 'a', '$': 's', '0': 'o', '1': 'i', '3': 'e',
    '5': 's', '7': 'h', '!': 'i', '|': 'l',
})
_NON_ALNUM_RE = re.compile(r'[^a-zA-Z\u0600-\u06FF]')
_DUP_RE = re.compile(r'(.)\1+')

def normalize_text(text: str):
    text = text.lower()
    text = _TASHKEEL_RE.sub('', text)
    text = text.translate(_LEET_MAP)
    cleaned = _NON_ALNUM_RE.sub('', text)
    collapsed = _DUP_RE.sub(r'\1', cleaned)
    return text, cleaned, collapsed

def _build_bad_words_regex(words):
    parts = []
    for w in words:
        if re.search(r'[\u0600-\u06FF]', w):
            parts.append(r'(?<![\u0600-\u06FF])' + re.escape(w) + r'(?![\u0600-\u06FF])')
        else:
            parts.append(r'(?<![a-zA-Z])' + re.escape(w) + r'(?![a-zA-Z])')
    return re.compile("|".join(parts), re.IGNORECASE)

BAD_WORDS_RE = _build_bad_words_regex(config.BAD_WORDS)
URL_REGEX = re.compile(
    r"(https?://\S+|discord\.gg/\S+|discord\.com/invite/\S+|www\.\S+)",
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════
# 🔒 القسم 9: نظام التوقيف
# ═══════════════════════════════════════════════════════════════

async def get_or_create_jail_channel(guild: discord.Guild,
                                     jail_role: discord.Role):
    channel = get_ch_jail(guild)

    if channel is None:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            jail_role: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        try:
            channel = await guild.create_text_channel("quarantine-zone", overwrites=overwrites)
            log.warning("لم أجد روم التوقيف -- أنشأت واحد جديد.")
        except discord.Forbidden:
            log.error("لا أملك صلاحية إنشاء روم التوقيف")
            return None
    else:
        try:
            await channel.set_permissions(
                jail_role, view_channel=True, send_messages=True, read_message_history=True
            )
            await channel.set_permissions(guild.default_role, view_channel=False)
        except Exception as e:
            log.warning("فشل تحديث صلاحيات روم التوقيف: %s", e)

    return channel

async def send_detention_report(guild, member, reason,
                                 duration_text="دائم",
                                 issued_by=None,
                                 evidence=None):
    """يرسل تقرير توقيف رسمي"""
    if issued_by is None:
        log_ch = get_ch_log_auto(guild)
    else:
        log_ch = get_ch_log_manual(guild)

    if not log_ch:
        log_ch = get_ch_admin_review(guild)

    if not log_ch:
        return

    now = discord.utils.utcnow()

    embed = discord.Embed(
        title="🏛️〢قرار توقيف رسمي",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "صدر قرار التوقيف من إدارة المملكة\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(139, 0, 0),
        timestamp=now,
    )
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)

    embed.add_field(
        name="🚔 المتوقف",
        value=member.mention + "\n`" + str(member.id) + "`",
        inline=False,
    )
    embed.add_field(
        name="⚖️ التهمة",
        value="```" + (reason or "لم تُحدد") + "```",
        inline=False,
    )
    embed.add_field(name="⏱️ المدة", value=duration_text, inline=True)
    embed.add_field(name="📅 التاريخ", value=now.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="🕐 الوقت", value=now.strftime("%H:%M"), inline=True)

    if issued_by:
        embed.add_field(
            name="👮 القاضي المُنفِّذ",
            value=issued_by.mention,
            inline=False,
        )
    else:
        embed.add_field(
            name="👮 القاضي المُنفِّذ",
            value="🤖 النظام التلقائي",
            inline=False,
        )

    if evidence:
        embed.add_field(name="📎 الدليل", value=evidence[:1024], inline=False)

    embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام العدالة")

    try:
        await log_ch.send(embed=embed)
    except Exception as e:
        log.warning("فشل إرسال تقرير التوقيف: %s", e)

async def apply_jail(guild: discord.Guild, member: discord.Member,
                     reason: str, duration_text: str = "دائم",
                     issued_by=None):
    if is_exempted(member):
        return False, "🛡️ هذا العضو محمي، لا يمكن توقيفه."
    if not isinstance(member, discord.Member):
        return False, "❌ العضو غير موجود في السيرفر."

    ok, why = bot_can_manage(member, guild)
    if not ok:
        return False, "❌ لا أستطيع توقيف " + member.mention + ": " + why

    jail_role = get_role_jail(guild)
    if not jail_role:
        return False, "❌ لم أجد رتبة التوقيف. أضف آيديها في config.py."

    if jail_role >= guild.me.top_role:
        return False, "❌ رتبة التوقيف أعلى من رتبة البوت. ارفع رتبة البوت فوقها."

    try:
        if jail_role not in member.roles:
            saved_roles[member.id] = [
                r.id for r in member.roles
                if r != guild.default_role and r != jail_role
            ]

        await get_or_create_jail_channel(guild, jail_role)
        await member.edit(roles=[jail_role], reason=reason)

        if member.voice:
            try:
                await member.move_to(None)
            except Exception:
                pass

        await save_state()

        # ⭐ إرسال تقرير التوقيف
        await send_detention_report(
            guild, member, reason,
            duration_text=duration_text,
            issued_by=issued_by,
        )

        return True, "🚔 تم تطبيق قرار التوقيف بنجاح."
    except discord.Forbidden:
        return False, "❌ البوت لا يملك صلاحية تعديل رتب هذا العضو."
    except Exception as e:
        log.exception("خطأ في apply_jail")
        return False, "❌ فشل التوقيف: " + str(e)

async def remove_jail(guild: discord.Guild, member: discord.Member):
    jail_role = get_role_jail(guild)
    if jail_role and jail_role in member.roles:
        try:
            await member.remove_roles(jail_role)
        except Exception as e:
            log.warning("فشل إزالة رتبة التوقيف: %s", e)

    if member.id in saved_roles:
        role_ids = saved_roles.pop(member.id)
        roles_to_restore = []
        for rid in role_ids:
            r = guild.get_role(rid)
            if r and r < guild.me.top_role:
                roles_to_restore.append(r)
        if roles_to_restore:
            try:
                await member.add_roles(*roles_to_restore, reason="فك التوقيف")
            except Exception as e:
                log.warning("فشل استعادة الرتب: %s", e)

    await save_state()
    return True, "🔓 تم الإفراج عن العضو واستعادة الرتب."# ═══════════════════════════════════════════════════════════════
# 🛡️ القسم 10: Anti-Nuke
# ═══════════════════════════════════════════════════════════════

def _now() -> float:
    return time.time()

def _prune_deque(dq: deque, window: int):
    cutoff = _now() - window
    while dq and dq[0] < cutoff:
        dq.popleft()

def record_action(guild_id: int, user_id: int, action: str) -> int:
    if action not in config.ANTI_NUKE_THRESHOLDS:
        return 0

    limit = config.ANTI_NUKE_THRESHOLDS[action]
    window = limit["seconds"]

    dq = NUKE_TRACKER[guild_id][user_id][action]
    dq.append(_now())
    _prune_deque(dq, window)
    return len(dq)

def is_nuke(guild_id: int, user_id: int, action: str) -> bool:
    if action not in config.ANTI_NUKE_THRESHOLDS:
        return False
    limit = config.ANTI_NUKE_THRESHOLDS[action]
    dq = NUKE_TRACKER[guild_id][user_id][action]
    _prune_deque(dq, limit["seconds"])
    return len(dq) > limit["count"]

def clear_user_tracker(guild_id: int, user_id: int, action=None):
    if guild_id not in NUKE_TRACKER:
        return
    if user_id not in NUKE_TRACKER[guild_id]:
        return
    if action:
        NUKE_TRACKER[guild_id][user_id][action].clear()
    else:
        NUKE_TRACKER[guild_id][user_id].clear()

async def get_audit_executor(guild: discord.Guild,
                             action: discord.AuditLogAction,
                             target_id: int,
                             limit: int = 5):
    try:
        async for entry in guild.audit_logs(limit=limit, action=action):
            if entry.target and entry.target.id == target_id:
                age = (discord.utils.utcnow() - entry.created_at).total_seconds()
                if age < 15:
                    return entry.user
    except discord.Forbidden:
        log.warning("لا أملك صلاحية قراءة audit log")
    except Exception as e:
        log.warning("خطأ في audit log: %s", e)
    return None

async def send_nuke_log(guild: discord.Guild, title: str,
                        color: discord.Color, fields: dict):
    log_ch = get_ch_log_nuke(guild) or get_ch_admin_review(guild)
    if not log_ch:
        return
    embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
    for name, value in fields.items():
        embed.add_field(name=name, value=str(value)[:1024], inline=False)
    try:
        await log_ch.send(embed=embed)
    except Exception:
        pass

async def _add_temp_jail_action(guild_id: int, user_id: int,
                                 duration_seconds: int,
                                 reason: str, moderator_id: int):
    """يضيف عقوبة توقيف مؤقت إلى قائمة extras.py"""
    try:
        import extras

        extras.TEMP_ACTIONS.append({
            "guild_id": guild_id,
            "user_id": user_id,
            "type": "jail",
            "until": time.time() + duration_seconds,
            "moderator": moderator_id,
            "reason": reason,
        })
        extras.save_temp_actions()
        log.info("أضيف توقيف مؤقت %d ثانية لـ %d", duration_seconds, user_id)
        return True
    except Exception as e:
        log.warning("فشل إضافة توقيف مؤقت: %s", e)
        return False

async def punish_nuker(guild: discord.Guild, member: discord.Member,
                       action: str, count: int) -> str:
    """
    عقوبة النيوك (بدون تحذير):
    - أول نيك: توقيف مؤقت 24 ساعة
    - ثاني نيك وأكثر: توقيف دائم
    """
    if member is None:
        return "لم أعرف من نفّذ العملية."
    if member.id == guild.owner_id:
        return "لا يمكن معاقبة مالك السيرفر."
    if is_exempted(member):
        return "العضو محمي -- لم تطبق العقوبة."

    NUKE_STRIKES[guild.id][member.id] += 1
    strikes = NUKE_STRIKES[guild.id][member.id]
    await save_nuke_strikes()

    reason = "Anti-Nuke: " + action + " (المرة " + str(strikes) + ")"

    if config.GRADUATED_NUKE_PUNISHMENT:
        if strikes == 1:
            # أول نيك: توقيف مؤقت 24 ساعة
            ok, msg = await apply_jail(
                guild, member,
                reason + " [توقيف مؤقت 24 ساعة]"
            )

            if ok:
                added = await _add_temp_jail_action(
                    guild.id, member.id, 86400,
                    "Anti-Nuke: " + action, bot.user.id,
                )
                if added:
                    return (
                        "🚔 توقيف مؤقت **24 ساعة** لـ " + member.mention
                        + " (نيك #1) -- سيفك تلقائياً"
                    )
                else:
                    return (
                        "🚔 توقيف مؤقت لـ " + member.mention
                        + " (نيك #1) -- ⚠️ فشل تسجيله للفك التلقائي"
                    )
            else:
                return "❌ فشل التوقيف: " + msg

        else:
            # ثاني نيك وأكثر: توقيف دائم
            ok, msg = await apply_jail(guild, member, reason + " [توقيف دائم]")

            if ok:
                return (
                    "🚔 توقيف **دائم** لـ " + member.mention
                    + " (نيك #" + str(strikes) + ") -- " + msg
                )
            else:
                return "❌ فشل التوقيف: " + msg

    if config.ANTI_NUKE_PUNISHMENT == "jail":
        ok, msg = await apply_jail(guild, member, reason)
        return msg

    return "عوقب"

async def handle_nuke_event(guild: discord.Guild, member: Optional[discord.Member],
                            action: str, target_desc: str,
                            restore_func=None):
    if not config.ANTI_NUKE_ENABLED:
        return
    if member is None:
        return
    if member.bot and member.id in trusted_bots:
        return
    if is_exempted(member):
        return

    count = record_action(guild.id, member.id, action)

    if not is_nuke(guild.id, member.id, action):
        return

    log.warning("NUKE detected: %s -- %s x %d", member, action, count)

    if restore_func:
        try:
            await restore_func()
        except Exception as e:
            log.exception("فشل الاسترجاع: %s", e)

    punishment = await punish_nuker(guild, member, action, count)

    # ─── اسم العملية بالعربي ───
    action_names = {
        "channel_delete": "🗑️ حذف روم",
        "channel_create": "➕ إنشاء روم",
        "channel_update": "✏️ تعديل روم",
        "role_delete":    "🗑️ حذف رتبة",
        "role_create":    "➕ إنشاء رتبة",
        "role_update":    "✏️ تعديل رتبة",
        "ban":            "🔨 حظر جماعي",
        "kick":           "👞 طرد جماعي",
        "bot_add":        "🤖 إضافة بوت",
        "webhook_create": "🔗 إنشاء Webhook",
    }
    action_ar = action_names.get(action, action)

    embed = discord.Embed(
        title="🚨 محاولة تخريب",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**تم كشف نشاط تخريبي وصدّه**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(139, 0, 0),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    embed.add_field(
        name="👤 المخرب",
        value=member.mention + "\n`" + str(member.id) + "`",
        inline=False,
    )
    embed.add_field(name="⚔️ العملية", value=action_ar, inline=True)
    embed.add_field(
        name="📊 عدد العمليات",
        value="**" + str(count) + "** خلال "
              + str(config.ANTI_NUKE_THRESHOLDS[action]["seconds"]) + "ث",
        inline=True,
    )
    embed.add_field(name="🎯 الهدف", value=target_desc[:500], inline=False)
    embed.add_field(name="🔨 العقوبة", value=punishment, inline=False)
    embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الحماية")

    log_ch = get_ch_log_nuke(guild) or get_ch_admin_review(guild)
    if log_ch:
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    clear_user_tracker(guild.id, member.id, action)

# ═══════════════════════════════════════════════════════════════
# 💾 القسم 11: النسخ الاحتياطية
# ═══════════════════════════════════════════════════════════════

def _backup_meta_load() -> dict:
    return _read_json(config.BACKUP_FILE, {
        "names": [],
        "icons": [],
        "banners": [],
    })

def _backup_meta_save(data: dict) -> None:
    _write_json(config.BACKUP_FILE, data)

def _add_to_history(lst: list, value, max_len: int):
    if value in lst:
        lst.remove(value)
    lst.insert(0, value)
    del lst[max_len:]

def backup_guild_name(guild: discord.Guild):
    if not config.BACKUP_ENABLED:
        return
    meta = _backup_meta_load()
    _add_to_history(meta["names"], guild.name, 10)
    _backup_meta_save(meta)

async def restore_guild_name(guild: discord.Guild):
    meta = _backup_meta_load()
    if len(meta["names"]) < 2:
        return False, "❌ لا يوجد اسم قديم محفوظ."

    previous = meta["names"][1]

    try:
        await guild.edit(name=previous, reason="Anti-Nuke: استرجاع الاسم")
        return True, "✅ تم استرجاع الاسم: " + previous
    except discord.Forbidden:
        return False, "❌ لا أملك صلاحية تعديل اسم السيرفر."
    except Exception as e:
        return False, "❌ فشل الاسترجاع: " + str(e)

async def backup_guild_icon(guild: discord.Guild):
    if not config.BACKUP_ENABLED or not guild.icon:
        return

    try:
        filename = str(guild.id) + "_" + str(int(_now())) + ".png"
        filepath = os.path.join(config.ICONS_DIR, filename)

        async with bot.http._HTTPClient__session.get(guild.icon.url) as resp:
            if resp.status == 200:
                data = await resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)

        meta = _backup_meta_load()
        _add_to_history(meta["icons"], {
            "url": guild.icon.url,
            "file": filename,
            "timestamp": int(_now()),
        }, config.BACKUP_MAX_ICONS)

        if len(meta["icons"]) > config.BACKUP_MAX_ICONS:
            for old in meta["icons"][config.BACKUP_MAX_ICONS:]:
                old_path = os.path.join(config.ICONS_DIR, old["file"])
                try:
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception:
                    pass
        meta["icons"] = meta["icons"][:config.BACKUP_MAX_ICONS]
        _backup_meta_save(meta)
    except Exception as e:
        log.warning("فشل حفظ الأيقونة: %s", e)

async def restore_guild_icon(guild: discord.Guild):
    meta = _backup_meta_load()
    if len(meta["icons"]) < 2:
        return False, "❌ لا توجد أيقونة قديمة محفوظة."

    prev = meta["icons"][1]
    filepath = os.path.join(config.ICONS_DIR, prev["file"])

    if not os.path.exists(filepath):
        return False, "❌ ملف الأيقونة القديمة غير موجود."

    try:
        with open(filepath, "rb") as f:
            await guild.edit(icon=f.read(), reason="Anti-Nuke: استرجاع الأيقونة")
        return True, "✅ تم استرجاع الأيقونة."
    except discord.Forbidden:
        return False, "❌ لا أملك صلاحية تعديل أيقونة السيرفر."
    except Exception as e:
        return False, "❌ فشل الاسترجاع: " + str(e)

async def backup_guild_banner(guild: discord.Guild):
    if not config.BACKUP_ENABLED or not guild.banner:
        return

    try:
        filename = str(guild.id) + "_" + str(int(_now())) + ".png"
        filepath = os.path.join(config.BANNERS_DIR, filename)

        async with bot.http._HTTPClient__session.get(guild.banner.url) as resp:
            if resp.status == 200:
                data = await resp.read()
                with open(filepath, "wb") as f:
                    f.write(data)

        meta = _backup_meta_load()
        _add_to_history(meta["banners"], {
            "url": guild.banner.url,
            "file": filename,
            "timestamp": int(_now()),
        }, config.BACKUP_MAX_BANNERS)

        if len(meta["banners"]) > config.BACKUP_MAX_BANNERS:
            for old in meta["banners"][config.BACKUP_MAX_BANNERS:]:
                old_path = os.path.join(config.BANNERS_DIR, old["file"])
                try:
                    if os.path.exists(old_path):
                        os.remove(old_path)
                except Exception:
                    pass
        meta["banners"] = meta["banners"][:config.BACKUP_MAX_BANNERS]
        _backup_meta_save(meta)
    except Exception as e:
        log.warning("فشل حفظ البانر: %s", e)

async def restore_guild_banner(guild: discord.Guild):
    meta = _backup_meta_load()
    if len(meta["banners"]) < 2:
        return False, "❌ لا يوجد بانر قديم محفوظ."

    prev = meta["banners"][1]
    filepath = os.path.join(config.BANNERS_DIR, prev["file"])

    if not os.path.exists(filepath):
        return False, "❌ ملف البانر القديم غير موجود."

    try:
        with open(filepath, "rb") as f:
            await guild.edit(banner=f.read(), reason="Anti-Nuke: استرجاع البانر")
        return True, "✅ تم استرجاع البانر."
    except discord.Forbidden:
        return False, "❌ لا أملك صلاحية تعديل بانر السيرفر."
    except Exception as e:
        return False, "❌ فشل الاسترجاع: " + str(e)

# ═══════════════════════════════════════════════════════════════
# 🗂️ القسم 12: Cache للرومات والرتب
# ═══════════════════════════════════════════════════════════════

def load_guild_cache():
    global GUILD_CACHE
    raw = _read_json(config.GUILD_CACHE_FILE, {})
    GUILD_CACHE = defaultdict(lambda: {"channels": {}, "roles": {}})
    for gid, data in raw.items():
        GUILD_CACHE[int(gid)] = {
            "channels": {int(k): v for k, v in data.get("channels", {}).items()},
            "roles": {int(k): v for k, v in data.get("roles", {}).items()},
        }

async def save_guild_cache():
    data = {}
    for gid, d in GUILD_CACHE.items():
        data[str(gid)] = {
            "channels": {str(k): v for k, v in d["channels"].items()},
            "roles": {str(k): v for k, v in d["roles"].items()},
        }
    await async_save_json(config.GUILD_CACHE_FILE, data)

def snapshot_channel(channel: discord.abc.GuildChannel) -> dict:
    base = {
        "name": channel.name,
        "position": channel.position,
        "category_id": channel.category_id,
    }

    overwrites = {}
    for target, ow in channel.overwrites.items():
        allow, deny = ow.pair()
        overwrites[str(target.id)] = {
            "type": "role" if isinstance(target, discord.Role) else "member",
            "allow": allow.value,
            "deny": deny.value,
        }
    base["overwrites"] = overwrites

    if isinstance(channel, discord.TextChannel):
        base.update({
            "kind": "text",
            "topic": channel.topic,
            "nsfw": channel.nsfw,
            "slowmode": channel.slowmode_delay,
        })
    elif isinstance(channel, discord.VoiceChannel):
        base.update({
            "kind": "voice",
            "bitrate": channel.bitrate,
            "user_limit": channel.user_limit,
        })
    elif isinstance(channel, discord.CategoryChannel):
        base["kind"] = "category"
    elif isinstance(channel, discord.StageChannel):
        base["kind"] = "stage"
    else:
        base["kind"] = "unknown"
    return base

def snapshot_role(role: discord.Role) -> dict:
    return {
        "name": role.name,
        "color": role.color.value,
        "permissions": role.permissions.value,
        "position": role.position,
        "hoist": role.hoist,
        "mentionable": role.mentionable,
        "unicode_emoji": role.unicode_emoji,
    }

def rebuild_overwrites(guild: discord.Guild, overwrites_data: dict) -> dict:
    result = {}
    for tid_str, ow in overwrites_data.items():
        tid = int(tid_str)
        target = guild.get_role(tid) if ow["type"] == "role" else guild.get_member(tid)
        if target is None:
            continue
        result[target] = discord.PermissionOverwrite.from_pair(
            discord.Permissions(ow["allow"]),
            discord.Permissions(ow["deny"]),
        )
    return result

async def cache_full_guild(guild: discord.Guild):
    channels_data = {}
    for ch in guild.channels:
        channels_data[ch.id] = snapshot_channel(ch)

    roles_data = {}
    for r in guild.roles:
        if r.is_default() or r.managed:
            continue
        roles_data[r.id] = snapshot_role(r)

    GUILD_CACHE[guild.id] = {"channels": channels_data, "roles": roles_data}
    await save_guild_cache()
    log.info("لقطة كاملة: %s (%d روم، %d رتبة)",
             guild.name, len(channels_data), len(roles_data))

async def restore_channel_from_cache(guild: discord.Guild, ch_id: int):
    cache = GUILD_CACHE.get(guild.id)
    if not cache or ch_id not in cache["channels"]:
        return None

    data = cache["channels"][ch_id]
    category = guild.get_channel(data.get("category_id")) if data.get("category_id") else None
    if category and not isinstance(category, discord.CategoryChannel):
        category = None

    try:
        overwrites = rebuild_overwrites(guild, data.get("overwrites", {}))
        kind = data.get("kind")

        if kind == "text":
            new_ch = await guild.create_text_channel(
                name=data["name"], category=category, position=data["position"],
                topic=data.get("topic"), nsfw=data.get("nsfw", False),
                slowmode_delay=data.get("slowmode", 0),
                overwrites=overwrites, reason="Anti-Nuke: استرجاع روم",
            )
        elif kind == "voice":
            new_ch = await guild.create_voice_channel(
                name=data["name"], category=category, position=data["position"],
                bitrate=data.get("bitrate", 64000),
                user_limit=data.get("user_limit", 0),
                overwrites=overwrites, reason="Anti-Nuke: استرجاع روم",
            )
        elif kind == "category":
            new_ch = await guild.create_category(
                name=data["name"], position=data["position"],
                overwrites=overwrites, reason="Anti-Nuke: استرجاع قسم",
            )
        elif kind == "stage":
            new_ch = await guild.create_stage_channel(
                name=data["name"], category=category, position=data["position"],
                overwrites=overwrites, reason="Anti-Nuke: استرجاع روم",
            )
        else:
            return None

        cache["channels"][new_ch.id] = snapshot_channel(new_ch)
        if ch_id in cache["channels"]:
            del cache["channels"][ch_id]
        await save_guild_cache()
        return new_ch
    except Exception as e:
        log.exception("فشل استرجاع الروم: %s", e)
        return None

async def restore_role_from_cache(guild: discord.Guild, role_id: int):
    cache = GUILD_CACHE.get(guild.id)
    if not cache or role_id not in cache["roles"]:
        return None

    data = cache["roles"][role_id]
    try:
        new_role = await guild.create_role(
            name=data["name"],
            color=discord.Color(data.get("color", 0)),
            permissions=discord.Permissions(data.get("permissions", 0)),
            hoist=data.get("hoist", False),
            mentionable=data.get("mentionable", False),
            unicode_emoji=data.get("unicode_emoji"),
            reason="Anti-Nuke: استرجاع رتبة",
        )
        try:
            await new_role.edit(position=data.get("position", new_role.position))
        except Exception:
            pass

        cache["roles"][new_role.id] = snapshot_role(new_role)
        if role_id in cache["roles"]:
            del cache["roles"][role_id]
        await save_guild_cache()
        return new_role
    except Exception as e:
        log.exception("فشل استرجاع الرتبة: %s", e)
        return None# ═══════════════════════════════════════════════════════════════
# 🚨 القسم 13: أحداث Anti-Nuke
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    await asyncio.sleep(0.7)

    cache = GUILD_CACHE.get(guild.id, {})
    cached_data = cache.get("channels", {}).get(channel.id, snapshot_channel(channel))
    GUILD_CACHE[guild.id]["channels"][channel.id] = cached_data
    await save_guild_cache()

    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_delete, channel.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        log.info("حذف روم بواسطة مستثنى (%s) -- تم التجاهل", executor)
        return

    await restore_channel_from_cache(guild, channel.id)

    if executor:
        log_ch = get_ch_log_changes(guild)
        if log_ch:
            embed = discord.Embed(
                title="🗑️ حذف روم",
                description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم حذف روم من السيرفر**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=discord.Color.from_rgb(139, 0, 0),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="📍 الروم المحذوف", value="`" + channel.name + "`", inline=False)
            embed.add_field(name="👮 بواسطة", value=executor.mention, inline=True)
            embed.add_field(name="🔄 الحالة", value="تم استرجاع الروم تلقائياً", inline=True)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

        await handle_nuke_event(guild, executor, "channel_delete", channel.name + " (" + str(channel.id) + ")")
    else:
        await send_nuke_log(guild, "⚠️ حذف روم (بدون معرفة الفاعل)", discord.Color.orange(), {"الروم المحذوف": channel.name})

@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    guild = channel.guild
    GUILD_CACHE[guild.id]["channels"][channel.id] = snapshot_channel(channel)
    await save_guild_cache()
    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_create, channel.id)

    if executor and not is_exempted(executor):
        log_ch = get_ch_log_changes(guild)
        if log_ch:
            embed = discord.Embed(
                title="📁 إنشاء روم",
                description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم إنشاء روم جديد**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="📍 الروم", value=channel.mention + "\n`" + channel.name + "`", inline=False)
            embed.add_field(name="🔧 النوع", value=type(channel).__name__.replace("Channel", ""), inline=True)
            embed.add_field(name="👮 بواسطة", value=executor.mention, inline=True)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    if executor:
        async def delete_new_channel():
            try: await channel.delete(reason="Anti-Nuke: حذف روم منشأ")
            except Exception: pass
        await handle_nuke_event(guild, executor, "channel_create", channel.name + " (" + str(channel.id) + ")", restore_func=delete_new_channel)

@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    guild = after.guild
    GUILD_CACHE[guild.id]["channels"][after.id] = snapshot_channel(after)
    await save_guild_cache()
    changes = []
    if before.name != after.name: changes.append("**الاسم:** `" + before.name + "` → `" + after.name + "`")
    if before.category_id != after.category_id: changes.append("**القسم:** تغيّر")
    if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
        if before.topic != after.topic: changes.append("**الموضوع:** تغيّر")
        if before.slowmode_delay != after.slowmode_delay: changes.append("**Slowmode:** `" + str(before.slowmode_delay) + "s` → `" + str(after.slowmode_delay) + "s`")

    if changes:
        log_ch = get_ch_log_changes(guild)
        if log_ch:
            executor = await get_audit_executor(guild, discord.AuditLogAction.channel_update, after.id)
            embed = discord.Embed(
                title="✏️ تعديل روم",
                description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم تعديل خصائص روم**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="📍 الروم", value=after.mention, inline=False)
            embed.add_field(name="📝 التغييرات", value="\n".join(changes)[:1024], inline=False)
            if executor: embed.add_field(name="👮 بواسطة", value=executor.mention, inline=False)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_update, after.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if executor: await handle_nuke_event(guild, executor, "channel_update", after.name)

@bot.event
async def on_guild_role_delete(role: discord.Role):
    guild = role.guild
    if role.is_default() or role.managed: return
    GUILD_CACHE[guild.id]["roles"][role.id] = snapshot_role(role)
    await save_guild_cache()
    await asyncio.sleep(0.7)
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_delete, role.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        log.info("حذف رتبة بواسطة مستثنى (%s) -- تم التجاهل", executor)
        return

    await restore_role_from_cache(guild, role.id)

    log_ch = get_ch_log_changes(guild)
    if log_ch:
        embed = discord.Embed(
            title="🗑️ حذف رتبة",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم حذف رتبة من السيرفر**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.from_rgb(139, 0, 0),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="👑 الرتبة", value="`" + role.name + "`", inline=False)
        if executor: embed.add_field(name="👮 بواسطة", value=executor.mention, inline=False)
        embed.add_field(name="🔄 الحالة", value="تم استرجاع الرتبة تلقائياً", inline=False)
        embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
        try: await log_ch.send(embed=embed)
        except Exception: pass

    if executor: await handle_nuke_event(guild, executor, "role_delete", role.name)

@bot.event
async def on_guild_role_create(role: discord.Role):
    guild = role.guild
    if role.managed: return
    GUILD_CACHE[guild.id]["roles"][role.id] = snapshot_role(role)
    await save_guild_cache()
    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_create, role.id)

    if executor and not is_exempted(executor):
        log_ch = get_ch_log_changes(guild)
        if log_ch:
            embed = discord.Embed(
                title="📁 إنشاء رتبة",
                description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم إنشاء رتبة جديدة**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="👑 الرتبة", value=role.mention + "\n`" + role.name + "`", inline=False)
            embed.add_field(name="👮 بواسطة", value=executor.mention, inline=False)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if executor:
        async def delete_new_role():
            try: await role.delete(reason="Anti-Nuke: حذف رتبة منشأة")
            except Exception: pass
        await handle_nuke_event(guild, executor, "role_create", role.name, restore_func=delete_new_role)

@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    guild = after.guild
    if after.is_default() or after.managed: return

    if before.permissions != after.permissions:
        if after.id in protected_roles_list:
            try: await after.edit(permissions=before.permissions, reason="Anti-Nuke: إرجاع صلاحيات رتبة محمية")
            except Exception as e: log.warning("فشل إرجاع الرتبة المحمية: %s", e)
            log_ch = get_ch_log_changes(guild)
            if log_ch:
                embed = discord.Embed(title="🛡️ محاولة تعديل رتبة محمية", color=discord.Color.red(), timestamp=discord.utils.utcnow())
                embed.add_field(name="👑 الرتبة", value=after.mention, inline=False)
                executor = await get_audit_executor(guild, discord.AuditLogAction.role_update, after.id)
                if executor: embed.add_field(name="👮 بواسطة", value=executor.mention, inline=False)
                try: await log_ch.send(embed=embed)
                except Exception: pass

    changes = []
    if before.name != after.name: changes.append("**الاسم:** `" + before.name + "` → `" + after.name + "`")
    if before.color != after.color: changes.append("**اللون:** تغيّر")
    if before.permissions != after.permissions: changes.append("**الصلاحيات:** تغيّرت")
    if before.hoist != after.hoist: changes.append("**Hoist:** تغيّر")

    if changes:
        log_ch = get_ch_log_changes(guild)
        if log_ch:
            executor = await get_audit_executor(guild, discord.AuditLogAction.role_update, after.id)
            embed = discord.Embed(
                title="✏️ تعديل رتبة",
                description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم تعديل رتبة**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="👑 الرتبة", value=after.mention, inline=False)
            embed.add_field(name="📝 التغييرات", value="\n".join(changes)[:1024], inline=False)
            if executor: embed.add_field(name="👮 بواسطة", value=executor.mention, inline=False)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

    GUILD_CACHE[guild.id]["roles"][after.id] = snapshot_role(after)
    await save_guild_cache()
    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_update, after.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if executor: await handle_nuke_event(guild, executor, "role_update", after.name)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    await asyncio.sleep(0.7)
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban, user.id)
    log_ch = get_ch_log_manual(guild)
    if log_ch and executor and not is_exempted(executor):
        embed = discord.Embed(
            title="🔨 حظر عضو",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم حظر عضو من السيرفر**\n━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.from_rgb(139, 0, 139),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.add_field(name="👤 العضو المحظور", value=str(user) + "\n`" + str(user.id) + "`", inline=False)
        embed.add_field(name="👮 بواسطة", value=executor.mention, inline=True)
        embed.add_field(name="📅 التاريخ", value=discord.utils.utcnow().strftime("%Y-%m-%d"), inline=True)
        embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق العقوبات")
        try: await log_ch.send(embed=embed)
        except Exception: pass

    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if not executor: return

    target_is_protected = (user.id == config.BOT_OWNER_ID or user.id in deputy_user_ids or user.id in protected_users_list or user.id == guild.owner_id)
    async def unban_user():
        try:
            await guild.unban(user, reason="Anti-Nuke: إلغاء حظر تخريبي")
            log.info("تم فك الحظر عن %s", user)
        except Exception as e: log.warning("فشل فك الحظر: %s", e)

    if target_is_protected:
        await unban_user()
        ok, msg = await apply_jail(guild, executor, "حظر عضو محمي: " + str(user), issued_by=None)
        log_ch = get_ch_log_auto(guild)
        if log_ch:
            embed = discord.Embed(title="🛡️ حظر عضو محمي", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم فك الحظر ومعاقبة المخالف**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(139, 0, 0), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(executor), icon_url=executor.display_avatar.url)
            embed.add_field(name="🛡️ العضو المحمي", value=str(user) + "\n`" + str(user.id) + "`", inline=False)
            embed.add_field(name="👤 المخالف", value=executor.mention + "\n`" + str(executor.id) + "`", inline=False)
            embed.add_field(name="🔨 العقوبة", value=msg, inline=False)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الحماية")
            try: await log_ch.send(embed=embed)
            except Exception: pass
        return

    await handle_nuke_event(guild, executor, "ban", str(user) + " (" + str(user.id) + ")", restore_func=unban_user)

@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild
    await asyncio.sleep(1.0)
    executor = await get_audit_executor(guild, discord.AuditLogAction.kick, member.id)

    if executor:
        log_ch = get_ch_log_manual(guild)
        if log_ch and not is_exempted(executor):
            embed = discord.Embed(title="👞 طرد عضو", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم طرد عضو من السيرفر**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(member), icon_url=member.display_avatar.url)
            embed.add_field(name="👤 العضو المطرود", value=str(member) + "\n`" + str(member.id) + "`", inline=False)
            embed.add_field(name="👮 بواسطة", value=executor.mention, inline=True)
            embed.add_field(name="📅 التاريخ", value=discord.utils.utcnow().strftime("%Y-%m-%d"), inline=True)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق العقوبات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

        if executor.id == bot.user.id or is_exempted(executor): return
        target_is_protected = (member.id == config.BOT_OWNER_ID or member.id in deputy_user_ids or member.id in protected_users_list or member.id == guild.owner_id)

        if target_is_protected:
            try: await member.send("⚠️ تم طردك من **" + guild.name + "** بشكل تخريبي.\nالبوت عاقب المسؤول عن ذلك.")
            except Exception: pass
            ok, msg = await apply_jail(guild, executor, "طرد عضو محمي: " + str(member), issued_by=None)
            log_ch = get_ch_log_auto(guild)
            if log_ch:
                embed = discord.Embed(title="🛡️ طرد عضو محمي", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم معاقبة المخالف**\n⚠️ لا يمكن إرجاع العضو المطرود\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(139, 0, 0), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(executor), icon_url=executor.display_avatar.url)
                embed.add_field(name="🛡️ العضو المحمي", value=str(member) + "\n`" + str(member.id) + "`", inline=False)
                embed.add_field(name="👤 المخالف", value=executor.mention + "\n`" + str(executor.id) + "`", inline=False)
                embed.add_field(name="🔨 العقوبة", value=msg, inline=False)
                embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الحماية")
                try: await log_ch.send(embed=embed)
                except Exception: pass
            return

        async def notify_kicked():
            try: await member.send("تم طردك من " + guild.name + " بشكل تخريبي.\nالبوت حاول حمايتك.")
            except Exception: pass
        await handle_nuke_event(guild, executor, "kick", str(member) + " (" + str(member.id) + ")", restore_func=notify_kicked)
        return

    # خروج عادي — لوق الخروج
    log_ch = get_ch_log_leave(guild)
    if log_ch:
        embed = discord.Embed(title="📤 عضو غادر المملكة", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n\n**" + str(member) + "** غادر السيرفر\n\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(139, 0, 0), timestamp=discord.utils.utcnow())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention + "\n`" + str(member.id) + "`", inline=False)
        embed.add_field(name="📊 الأعضاء الآن", value="**" + str(guild.member_count) + "**", inline=True)
        embed.add_field(name="📅 تاريخ المغادرة", value="<t:" + str(int(discord.utils.utcnow().timestamp())) + ":R>", inline=True)
        embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق الخروج")
        try: await log_ch.send(embed=embed)
        except Exception: pass

@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    guild = entry.guild
    if entry.action == discord.AuditLogAction.bot_add:
        target = entry.target
        if not isinstance(target, discord.Member) or is_exempted(entry.user): return
        log_ch = get_ch_log_guild(guild) or get_ch_admin_review(guild)
        if log_ch:
            embed = discord.Embed(title="🤖 إضافة بوت", color=discord.Color.purple(), timestamp=discord.utils.utcnow())
            embed.add_field(name="البوت", value=str(target) + " (`" + str(target.id) + "`)", inline=False)
            embed.add_field(name="بواسطة", value=entry.user.mention, inline=False)
            try: await log_ch.send(embed=embed)
            except Exception: pass
        if target.id not in trusted_bots:
            try: await target.kick(reason="Anti-Nuke: بوت غير موثوق")
            except Exception: pass
            await handle_nuke_event(guild, entry.user, "bot_add", str(target) + " (" + str(target.id) + ")")
    elif entry.action == discord.AuditLogAction.webhook_create:
        if is_exempted(entry.user): return
        log_ch = get_ch_log_guild(guild) or get_ch_admin_review(guild)
        if log_ch:
            embed = discord.Embed(title="🔗 إنشاء Webhook", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
            embed.add_field(name="القناة", value=str(entry.target), inline=False)
            embed.add_field(name="بواسطة", value=entry.user.mention, inline=False)
            try: await log_ch.send(embed=embed)
            except Exception: pass
        async def del_webhook():
            try:
                if hasattr(entry.target, "webhooks"):
                    webhooks = await entry.target.webhooks()
                    for wh in webhooks:
                        if wh.user and wh.user.id == entry.user.id: await wh.delete(reason="Anti-Nuke: webhook مشبوه")
            except Exception: pass
        await handle_nuke_event(guild, entry.user, "webhook_create", "في " + str(entry.target), restore_func=del_webhook)

@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    guild = after
    if before.name != after.name:
        log_ch = get_ch_log_auto(guild)
        if log_ch:
            embed = discord.Embed(title="🌐 تغيير اسم السيرفر", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.add_field(name="القديم", value="`" + before.name + "`", inline=True)
            embed.add_field(name="الجديد", value="`" + after.name + "`", inline=True)
            try: await log_ch.send(embed=embed)
            except Exception: pass
        await asyncio.sleep(1)
        executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update, guild.id)
        if executor and not is_exempted(executor) and executor.id != bot.user.id:
            ok, msg = await restore_guild_name(guild)
            if ok: await send_nuke_log(guild, "🛡️ استرجاع اسم السيرفر", discord.Color.green(), {"الاسم الأصلي": before.name, "بواسطة": executor.mention})

    if before.icon != after.icon:
        log_ch = get_ch_log_auto(guild)
        if log_ch:
            embed = discord.Embed(title="🖼️ تغيير أيقونة السيرفر", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            try: await log_ch.send(embed=embed)
            except Exception: pass
        await asyncio.sleep(1)
        executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update, guild.id)
        if executor and not is_exempted(executor) and executor.id != bot.user.id:
            ok, msg = await restore_guild_icon(guild)
            if ok: await send_nuke_log(guild, "🛡️ استرجاع أيقونة السيرفر", discord.Color.green(), {"بواسطة": executor.mention})

    if before.banner != after.banner:
        log_ch = get_ch_log_auto(guild)
        if log_ch:
            embed = discord.Embed(title="🖼️ تغيير بانر السيرفر", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            try: await log_ch.send(embed=embed)
            except Exception: pass
        await asyncio.sleep(1)
        executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update, guild.id)
        if executor and not is_exempted(executor) and executor.id != bot.user.id:
            ok, msg = await restore_guild_banner(guild)
            if ok: await send_nuke_log(guild, "🛡️ استرجاع بانر السيرفر", discord.Color.green(), {"بواسطة": executor.mention})

# ═══════════════════════════════════════════════════════════════
# 👋 القسم 15: أحداث الأعضاء
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    try:
        invite_url = None
        try:
            invites = await guild.invites()
            if invites: invite_url = invites[0].url
        except Exception: pass
        dm_embed = discord.Embed(
            title="🇸🇦〢Kingdom of Saudi Arabia",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━\n\n**أهلاً وسهلاً بك في المملكة! 🎉**\n\nنرجو منك الاطلاع على القوانين:\n\n" + config.RULES_TEXT + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.from_rgb(0, 122, 61),
        )
        dm_embed.set_footer(text="🇸🇦 نتشرف بانضمامك إلينا")
        view = View()
        if invite_url:
            view.add_item(Button(label="🇸🇦 سيرفر " + guild.name, url=invite_url, style=discord.ButtonStyle.link))
            await member.send(embed=dm_embed, view=view)
        else: await member.send(embed=dm_embed)
    except discord.Forbidden: pass
    except Exception as e: log.warning("فشل إرسال DM الترحيب: %s", e)

    welcome_ch = get_ch_welcome(guild)
    if welcome_ch:
        embed = discord.Embed(
            title="🇸🇦 عضو جديد في المملكة!",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━\n\n**أهلاً وسهلاً " + member.mention + "** 🎉\n\nنرحب بك في **🇸🇦〢Kingdom of Saudi Arabia**\nنتمنى لك وقتاً ممتعاً معنا\n\n━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 **عدد الأعضاء:** `#" + str(guild.member_count) + "`\n📅 **وقت الانضمام:** <t:" + str(int(discord.utils.utcnow().timestamp())) + ":R>\n━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=discord.Color.from_rgb(0, 122, 61),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        try: await welcome_ch.send(content=member.mention, embed=embed)
        except Exception as e: log.warning("فشل إرسال رسالة الترحيب: %s", e)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.roles != after.roles:
        if is_exempted(after) and after.id != bot.user.id:
            removed = [r for r in before.roles if r not in after.roles]
            jail_role = get_role_jail(after.guild)
            meaningful_removed = [r for r in removed if r != after.guild.default_role and r != jail_role]
            if meaningful_removed:
                await asyncio.sleep(0.5)
                executor = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
                if executor and not is_exempted(executor) and executor.id != bot.user.id:
                    try: await after.add_roles(*meaningful_removed, reason="حماية: استرجاع رتب عضو محمي")
                    except Exception as e: log.warning("فشل استرجاع الرتب: %s", e)
                    ok, msg = await apply_jail(after.guild, executor, "محاولة سحب رتب من عضو محمي: " + str(after))
                    log_ch = get_ch_log_auto(after.guild)
                    if log_ch:
                        embed = discord.Embed(title="🛡️ محاولة سحب رتب من عضو محمي", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم كشف المحاولة وصدّها**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(139, 0, 0), timestamp=discord.utils.utcnow())
                        embed.set_author(name=str(executor), icon_url=executor.display_avatar.url)
                        embed.add_field(name="🛡️ العضو المحمي", value=after.mention + "\n`" + str(after.id) + "`", inline=False)
                        embed.add_field(name="👤 المخالف", value=executor.mention + "\n`" + str(executor.id) + "`", inline=False)
                        embed.add_field(name="👑 الرتب المسحوبة", value=", ".join(r.mention for r in meaningful_removed)[:1024], inline=False)
                        embed.add_field(name="🔨 العقوبة", value=msg, inline=False)
                        embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الحماية")
                        try: await log_ch.send(embed=embed)
                        except Exception: pass

    if before.timed_out_until != after.timed_out_until:
        if is_exempted(after) and after.timed_out_until is not None:
            if after.timed_out_until > discord.utils.utcnow():
                await asyncio.sleep(0.5)
                executor = await get_audit_executor(after.guild, discord.AuditLogAction.member_update, after.id)
                if executor and not is_exempted(executor) and executor.id != bot.user.id:
                    try: await after.timeout(None, reason="حماية: إزالة تايم آوت")
                    except Exception as e: log.warning("فشل إزالة التايم آوت: %s", e)
                    ok, msg = await apply_jail(after.guild, executor, "محاولة تايم آوت لعضو محمي: " + str(after))
                    log_ch = get_ch_log_auto(after.guild)
                    if log_ch:
                        embed = discord.Embed(title="🛡️ محاولة تايم آوت لعضو محمي", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم كشف المحاولة وإلغاؤها**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(139, 0, 0), timestamp=discord.utils.utcnow())
                        embed.set_author(name=str(executor), icon_url=executor.display_avatar.url)
                        embed.add_field(name="🛡️ العضو المحمي", value=after.mention + "\n`" + str(after.id) + "`", inline=False)
                        embed.add_field(name="👤 المخالف", value=executor.mention + "\n`" + str(executor.id) + "`", inline=False)
                        embed.add_field(name="🔨 العقوبة", value=msg, inline=False)
                        embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الحماية")
                        try: await log_ch.send(embed=embed)
                        except Exception: pass

    if before.timed_out_until != after.timed_out_until:
        log_ch = get_ch_log_manual(after.guild)
        if log_ch:
            await asyncio.sleep(0.5)
            executor = await get_audit_executor(after.guild, discord.AuditLogAction.member_update, after.id)
            if after.timed_out_until is not None and (before.timed_out_until is None or after.timed_out_until > before.timed_out_until):
                duration = after.timed_out_until - discord.utils.utcnow()
                total_sec = int(duration.total_seconds())
                hours = total_sec // 3600
                minutes = (total_sec % 3600) // 60
                if hours >= 1:
                    duration_text = str(hours) + " ساعة"
                    if minutes > 0: duration_text += " و " + str(minutes) + " دقيقة"
                else: duration_text = str(minutes) + " دقيقة"
                until_ts = int(after.timed_out_until.timestamp())
                embed = discord.Embed(title="⏱️ تم إعطاء تايم آوت", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                embed.add_field(name="العضو", value=after.mention + " (`" + str(after.id) + "`)", inline=False)
                embed.add_field(name="المدة", value=duration_text, inline=True)
                embed.add_field(name="ينتهي", value="<t:" + str(until_ts) + ":R>", inline=True)
                if executor: embed.add_field(name="بواسطة", value=executor.mention, inline=False)
                embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق العقوبات")
                try: await log_ch.send(embed=embed)
                except Exception: pass
            elif after.timed_out_until is None and before.timed_out_until is not None:
                embed = discord.Embed(title="✅ تم إزالة التايم آوت", color=discord.Color.green(), timestamp=discord.utils.utcnow())
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                embed.add_field(name="العضو", value=after.mention + " (`" + str(after.id) + "`)", inline=False)
                if executor: embed.add_field(name="بواسطة", value=executor.mention, inline=False)
                embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق العقوبات")
                try: await log_ch.send(embed=embed)
                except Exception: pass

    if before.roles != after.roles and getattr(config, "ROLE_NOTIFY_ENABLED", True):
        added_roles = [r for r in after.roles if r not in before.roles]
        ignore_names = getattr(config, "ROLE_NOTIFY_IGNORE", [])
        meaningful_added = [r for r in added_roles if r.name not in ignore_names and r != after.guild.default_role]
        if meaningful_added and after.id != bot.user.id:
            roles_text = "\n".join("• " + r.mention for r in meaningful_added)
            try:
                await after.send("🎖️ **رتبة جديدة!**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📍 **السيرفر:** " + after.guild.name + "\n\n✨ **تم منحك:**\n" + roles_text + "\n\n💡 يمكنك الآن الاستمتاع بميزات الرتبة!\n\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🇸🇦〢Kingdom of Saudi Arabia")
            except discord.Forbidden: pass
            except Exception as e: log.warning("فشل DM الرتبة: %s", e)

    if before.roles != after.roles:
        log_ch = get_ch_log_changes(after.guild)
        if log_ch:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            embed = discord.Embed(title="👑 تحديث رتب", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم تحديث رتب عضو**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.add_field(name="👤 العضو", value=after.mention + "\n`" + str(after.id) + "`", inline=False)
            if added: embed.add_field(name="🟢 رتب مُضافة", value=", ".join(r.mention for r in added)[:1024], inline=False)
            if removed: embed.add_field(name="🔴 رتب مُزالة", value=", ".join(r.mention for r in removed)[:1024], inline=False)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

    if before.nick != after.nick:
        log_ch = get_ch_log_changes(after.guild)
        if log_ch:
            embed = discord.Embed(title="✏️ تغيّر اللقب", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم تغيير لقب عضو**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.add_field(name="👤 العضو", value=after.mention + "\n`" + str(after.id) + "`", inline=False)
            embed.add_field(name="📛 القديم", value="```" + (before.nick or "لا يوجد") + "```", inline=True)
            embed.add_field(name="✨ الجديد", value="```" + (after.nick or "لا يوجد") + "```", inline=True)
            embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
            try: await log_ch.send(embed=embed)
            except Exception: pass

# ═══════════════════════════════════════════════════════════════
# 📝 القسم 16: on_message_delete
# ═══════════════════════════════════════════════════════════════

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild: return
    log_ch = get_ch_log_changes(message.guild)
    if not log_ch: return
    embed = discord.Embed(title="🗑️ حذف رسالة", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم حذف رسالة**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(139, 0, 0), timestamp=discord.utils.utcnow())
    embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
    embed.add_field(name="👤 صاحب الرسالة", value=message.author.mention + "\n`" + str(message.author.id) + "`", inline=False)
    embed.add_field(name="📍 الروم", value=message.channel.mention, inline=True)
    embed.add_field(name="📅 التاريخ", value=discord.utils.utcnow().strftime("%Y-%m-%d"), inline=True)
    content = (message.content or "*(وسائط فقط)*")[:1000]
    embed.add_field(name="💬 المحتوى", value="```" + content + "```", inline=False)
    embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — لوق التعديلات")
    try: await log_ch.send(embed=embed)
    except Exception: pass

# ═══════════════════════════════════════════════════════════════
# 💬 القسم 17: كشف المخالفات + on_message
# ═══════════════════════════════════════════════════════════════

def detect_violation(message: discord.Message):
    raw = message.content or ""
    if not raw.strip(): return None
    if message.mention_everyone: return "منشن الجميع (@everyone / @here)"
    _, cleaned, collapsed = normalize_text(raw)
    if BAD_WORDS_RE.search(cleaned) or BAD_WORDS_RE.search(collapsed): return "السب والشتم / ألفاظ نابية"
    url_check_text = raw
    for att in message.attachments: url_check_text = url_check_text.replace(att.url, "")
    if URL_REGEX.search(url_check_text): return "إرسال روابط أو دعوات سيرفرات"
    return None

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild: return
    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return
    if is_exempted(message.author): return
    violation = detect_violation(message)
    if not violation: return

    guild = message.guild
    member = message.author
    try: await message.delete()
    except Exception: pass

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    USER_WARNINGS.setdefault(member.id, []).append({"reason": violation, "warned_by": "النظام التلقائي", "date": now_str})
    warn_count = len(USER_WARNINGS[member.id])
    action_taken = ""

    if violation == "السب والشتم / ألفاظ نابية":
        ok, msg = await apply_jail(guild, member, "مخالفة: " + violation, duration_text="دائم", issued_by=None)
        action_taken = msg + " (توقيف دائم)"
    else:
        try:
            until = discord.utils.utcnow() + datetime.timedelta(hours=1)
            await member.timeout(until, reason="إنذار " + str(warn_count) + ": " + violation)
            action_taken = "إنذار رقم " + str(warn_count) + " + تايم آوت ساعة."
        except discord.Forbidden: action_taken = "إنذار رقم " + str(warn_count) + " (فشل التايم آوت)."
        except Exception as e: action_taken = "إنذار رقم " + str(warn_count) + " (فشل: " + str(e) + ")"
        if warn_count >= 3:
            ok, msg = await apply_jail(guild, member, "بلوغ " + str(warn_count) + " إنذارات", duration_text="دائم", issued_by=None)
            action_taken += "\n" + msg + " (توقيف دائم)"

    await save_warnings()
    try:
        await member.send("🚨 **تنبيه إداري عاجل**\n━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📍 **السيرفر:** " + guild.name + "\n⚖️ **المخالفة:** " + violation + "\n🔨 **الإجراء:** " + action_taken + "\n📊 **إجمالي تحذيراتك:** `" + str(warn_count) + "`\n\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🇸🇦〢Kingdom of Saudi Arabia")
    except Exception: pass

    admin_ch = get_ch_log_auto(guild)
    if admin_ch:
        embed = discord.Embed(title="🚨 رصد مخالفة", description="━━━━━━━━━━━━━━━━━━━━━━━━━\n**تم كشف مخالفة تلقائياً**\n━━━━━━━━━━━━━━━━━━━━━━━━━", color=discord.Color.from_rgb(220, 20, 60), timestamp=discord.utils.utcnow())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="👤 العضو", value=member.mention + "\n`" + str(member.id) + "`", inline=False)
        embed.add_field(name="📍 الروم", value=message.channel.mention, inline=True)
        embed.add_field(name="⚖️ المخالفة", value="`" + violation + "`", inline=True)
        embed.add_field(name="⚠️ الإجراء", value=action_taken, inline=False)
        embed.add_field(name="📊 التحذيرات", value="**" + str(warn_count) + " / 3**", inline=True)
        content = (message.content or "")[:1000] or "*(وسائط فقط)*"
        embed.add_field(name="💬 الرسالة", value="```" + content + "```", inline=False)
        embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الرقابة")
        try: await admin_ch.send(embed=embed)
        except Exception: pass# ═══════════════════════════════════════════════════════════════
# 📜 القسم 19: البرقيات (Ticket System) + الملاحظات + إعادة التشغيل
# ═══════════════════════════════════════════════════════════════
class TicketModal(Modal, title="📜 إرسال برقية رسمية"):
    subject = TextInput(label="الموضوع", placeholder="اكتب موضوع البرقية...", required=True, max_length=100)
    problem = TextInput(label="المشكلة / الطلب", style=discord.TextStyle.paragraph, placeholder="اشرح مشكلتك...", required=True, max_length=1000)
    extra = TextInput(label="ملاحظات إضافية (اختياري)", style=discord.TextStyle.paragraph, required=False, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = get_cat_ticket(guild)
        if not category:
            await interaction.response.send_message("❌ لم أجد تصنيف البرقيات.", ephemeral=True)
            return
        existing = next((ch for ch in category.text_channels if str(interaction.user.id) in ch.name), None)
        if existing:
            await interaction.response.send_message(f"⚠️ لديك برقية مفتوحة: {existing.mention}", ephemeral=True)
            return
            
        ticket_role = get_role_ticket(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if ticket_role: overwrites[ticket_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        try:
            ch = await guild.create_text_channel(f"ticket-{interaction.user.id}", category=category, overwrites=overwrites)
        except Exception as e:
            await interaction.response.send_message(f"❌ فشل فتح البرقية: {e}", ephemeral=True)
            return

        embed = discord.Embed(title="📜 برقية رسمية", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.add_field(name="👤 العضو", value=interaction.user.mention, inline=False)
        embed.add_field(name="📋 الموضوع", value=f"```{self.subject.value}```", inline=False)
        embed.add_field(name="📝 التفاصيل", value=self.problem.value[:1024], inline=False)
        if self.extra.value: embed.add_field(name="📎 ملاحظات", value=self.extra.value[:1024], inline=False)
        
        try: await ch.send(content=f"{interaction.user.mention} | {ticket_role.mention if ticket_role else ''}", embed=embed, view=CloseTicketButton())
        except Exception: pass
        
        await interaction.response.send_message(f"✅ تم فتح برقيتك: {ch.mention}", ephemeral=True)

class NoteModal(Modal, title="📝 إرسال ملاحظة"):
    note = TextInput(label="الملاحظة", style=discord.TextStyle.paragraph, placeholder="اكتب ملاحظتك...", required=True, max_length=1000)
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📝 ملاحظة جديدة", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 العضو", value=interaction.user.mention, inline=False)
        embed.add_field(name="📝 الملاحظة", value=f"```{self.note.value[:1000]}```", inline=False)
        
        log_ch = get_ch_admin_review(interaction.guild)
        if log_ch:
            try: await log_ch.send(embed=embed)
            except Exception: pass
        try:
            owner = await interaction.client.fetch_user(config.BOT_OWNER_ID)
            if owner: await owner.send(embed=embed)
        except Exception: pass
        await interaction.response.send_message("✅ **تم إرسال ملاحظتك للإدارة بنجاح!**", ephemeral=True)

class TicketButtonView(View):
    def __init__(self): super().__init__(timeout=None)
    
    @discord.ui.button(label="📜 إرسال برقية", style=discord.ButtonStyle.success, custom_id="btn_ticket")
    async def send_ticket(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(TicketModal())
    
    @discord.ui.button(label="📝 إرسال ملاحظة", style=discord.ButtonStyle.primary, custom_id="btn_note")
    async def send_note(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(NoteModal())
    
    @discord.ui.button(label="🔄 إعادة تشغيل الأزرار", style=discord.ButtonStyle.danger, custom_id="btn_restart")
    async def restart_panel(self, interaction: discord.Interaction, button: Button):
        if not await require_control(interaction): return
        await interaction.response.defer(ephemeral=True)
        bot.add_view(TicketButtonView())
        bot.add_view(CloseTicketButton())
        bot.add_view(ApplicationButtonView())
        await interaction.message.edit(view=TicketButtonView())
        await interaction.followup.send("✅ تم إعادة تشغيل الأزرار بنجاح!", ephemeral=True)

class CloseTicketButton(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 إغلاق البرقية", style=discord.ButtonStyle.red, custom_id="btn_close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        roles = interaction.user.roles if isinstance(interaction.user, discord.Member) else []
        if not ((get_role_ticket(interaction.guild) in roles) or (get_role_minister(interaction.guild) in roles) or has_control(interaction.user.id)):
            await interaction.response.send_message("❌ لا تمتلك الصلاحية.", ephemeral=True)
            return
        await interaction.response.send_message("🔒 سيتم إغلاق البرقية خلال دقيقة...", ephemeral=True)
        await asyncio.sleep(60)
        try: await interaction.channel.delete()
        except Exception: pass

# ═══════════════════════════════════════════════════════════════
# 🇸🇦 القسم 20: نظام الجنسية
# ═══════════════════════════════════════════════════════════════
class ApplicationModal(Modal, title="🇸🇦 استمارة الهوية"):
    q1 = TextInput(label="الاسم", placeholder="الاسم الذي سيظهر كلقب...", required=True, max_length=32)
    q2 = TextInput(label="العمر", placeholder="عمرك...", required=True, max_length=10)
    q3 = TextInput(label="سبب الانضمام", style=discord.TextStyle.paragraph, required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        admin_ch = get_ch_log_tickets(interaction.guild)
        if not admin_ch:
            await interaction.response.send_message("❌ لم أجد روم استقبال التقديمات.", ephemeral=True)
            return
        embed = discord.Embed(title="🇸🇦 طلب جنسية جديد", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="المتقدم", value=interaction.user.mention, inline=False)
        embed.add_field(name="الاسم", value=self.q1.value, inline=False)
        embed.add_field(name="العمر", value=self.q2.value, inline=False)
        embed.add_field(name="السبب", value=self.q3.value, inline=False)
        await admin_ch.send(embed=embed, view=AdminDecisionView(member=interaction.user, apply_name=self.q1.value))
        await interaction.response.send_message("✅ تم إرسال طلبك للإدارة!", ephemeral=True)

class ApplicationButtonView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🇸🇦 التقديم للجنسية", style=discord.ButtonStyle.success, custom_id="btn_apply")
    async def apply_button(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(ApplicationModal())

class AdminDecisionView(View):
    def __init__(self, member: discord.Member, apply_name: str = ""):
        super().__init__(timeout=None)
        self.member = member
        self.apply_name = apply_name or ""

    async def _check_perm(self, interaction: discord.Interaction) -> bool:
        roles = interaction.user.roles if isinstance(interaction.user, discord.Member) else []
        if (get_role_apply(interaction.guild) in roles) or (get_role_minister(interaction.guild) in roles) or has_control(interaction.user.id):
            return True
        await interaction.response.send_message("❌ لا تمتلك الصلاحية.", ephemeral=True)
        return False

    @discord.ui.button(label="✅ قبول", style=discord.ButtonStyle.success, custom_id="btn_accept")
    async def accept_app(self, interaction: discord.Interaction, button: Button):
        if not await self._check_perm(interaction): return
        citizen_role = get_role_citizen(interaction.guild)
        role_status = ""
        if citizen_role:
            try:
                await self.member.add_roles(citizen_role)
                role_status = f"\n🎖️ الرتبة: {citizen_role.mention}"
            except Exception: role_status = "\n⚠️ فشل إعطاء الرتبة"
            
        nick_status = ""
        clean_name = self.apply_name.strip()[:32]
        if clean_name:
            try:
                await self.member.edit(nick=clean_name)
                nick_status = f"\n📝 اللقب: {clean_name}"
            except Exception: nick_status = "\n⚠️ فشل تغيير اللقب"
            
        try: await self.member.send(f"🎉 **مبروك!**\nتم قبول طلبك.\n{role_status}\n{nick_status}")
        except Exception: pass
        
        await interaction.message.edit(view=None)
        await interaction.response.send_message(f"✅ تم قبول {self.member.mention}", ephemeral=True)

    @discord.ui.button(label="❌ رفض", style=discord.ButtonStyle.red, custom_id="btn_reject")
    async def reject_app(self, interaction: discord.Interaction, button: Button):
        if not await self._check_perm(interaction): return
        try: await self.member.send("❌ نأسف، تم رفض طلبك.")
        except Exception: pass
        await interaction.message.edit(view=None)
        await interaction.response.send_message(f"❌ تم رفض {self.member.mention}", ephemeral=True)

# ═══════════════════════════════════════════════════════════════
# ⚙️ القسم 21: الأوامر العامة (التي طلبتها)
# ═══════════════════════════════════════════════════════════════
@bot.tree.command(name="بانل_البرقيات", description="📜 إرسال بانل البرقيات الرسمية")
async def send_ticket_panel(interaction: discord.Interaction):
    if not await require_control(interaction): return
    ch = get_ch_ticket_panel(interaction.guild)
    if not ch: return await interaction.response.send_message("❌ لم أجد روم بانل البرقيات.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="📜 البرقيات الرسمية", color=discord.Color.from_rgb(0, 122, 61), description="━━━━━━━━━━━━━━━━━━━━━━━━━\n\n**هل تحتاج مساعدة؟** 🇸🇦\n\nأرسل برقية رسمية للإدارة أو ملاحظة.\n\n━━━━━━━━━━━━━━━━━━━━━━━━━\n📝 **الخطوات:**\n• اضغط الزر أدناه\n• اكتب موضوعك\n• سيُفتح لك روم خاص أو ستُرسل ملاحظتك\n━━━━━━━━━━━━━━━━━━━━━━━━━")
    embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — مركز البرقيات")
    await ch.send(embed=embed, view=TicketButtonView())
    await interaction.followup.send("✅ تم إرسال بانل البرقيات.", ephemeral=True)

@bot.tree.command(name="بانل_الجنسية", description="🇸🇦 إرسال بانل التقديم للجنسية")
async def send_apply_panel(interaction: discord.Interaction):
    if not await require_control(interaction): return
    ch = get_ch_apply_panel(interaction.guild)
    if not ch: return await interaction.response.send_message("❌ لم أجد روم بانل الجنسية.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(title="🇸🇦 التقديم للجنسية", color=discord.Color.from_rgb(0, 122, 61), description="━━━━━━━━━━━━━━━━━━━━━━━━━\n\n📜 **للحصول على الجنسية:**\nاضغط على الزر أدناه\n\n━━━━━━━━━━━━━━━━━━━━━━━━━")
    embed.set_footer(text="🇸🇦〢Kingdom of Saudi Arabia — نظام الجنسية")
    await ch.send(embed=embed, view=ApplicationButtonView())
    await interaction.followup.send("✅ تم إرسال بانل الجنسية.", ephemeral=True)

@bot.tree.command(name="أمر_توقيف", description="🚔 إصدار قرار توقيف")
@discord.app_commands.describe(member="العضو", reason="السبب")
async def jail_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "لم يحدد"):
    if not await require_control(interaction): return
    ok, msg = await apply_jail(interaction.guild, member, reason, issued_by=interaction.user)
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="أمر_إفراج", description="🔓 فك توقيف عضو")
@discord.app_commands.describe(member="العضو")
async def unjail_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction): return
    ok, msg = await remove_jail(interaction.guild, member)
    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="إنذار_رسمي", description="⚠️ إنذار رسمي لعضو")
@discord.app_commands.describe(member="العضو", reason="السبب")
async def warn_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "لم يحدد"):
    if not await require_control(interaction): return
    USER_WARNINGS.setdefault(member.id, []).append({"reason": reason, "date": str(datetime.datetime.now())})
    await save_warnings()
    if len(USER_WARNINGS[member.id]) >= 3: await apply_jail(interaction.guild, member, "3 إنذارات")
    await interaction.response.send_message(f"✅ تم إنذار {member.mention}. الإجمالي: {len(USER_WARNINGS[member.id])}", ephemeral=True)

@bot.tree.command(name="سجل_الإنذارات", description="📋 عرض سجل الإنذارات")
@discord.app_commands.describe(member="العضو")
async def log_cmd(interaction: discord.Interaction, member: discord.Member):
    warns = USER_WARNINGS.get(member.id, [])
    text = "\n".join([f"- {w['reason']}" for w in warns]) or "لا يوجد إنذارات."
    await interaction.response.send_message(embed=discord.Embed(title=f"سجل {member.name}", description=text, color=discord.Color.orange()), ephemeral=True)

@bot.tree.command(name="تفتيش_المملكة", description="🔍 فحص إعدادات المملكة")
async def check_cmd(interaction: discord.Interaction):
    if not await require_control(interaction): return
    await interaction.response.send_message("✅ النظام يعمل والإعدادات سليمة.", ephemeral=True)

@bot.tree.command(name="تعيين_وزير", description="👑 تعيين وزير")
@discord.app_commands.describe(member="العضو")
async def deputy_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_owner(interaction): return
    if member.id not in deputy_user_ids: 
        deputy_user_ids.append(member.id); await save_state(); await interaction.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="حماية_مواطن", description="🛡️ حماية عضو من العقوبات")
@discord.app_commands.describe(member="العضو")
async def protect_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction): return
    if member.id not in protected_users_list: 
        protected_users_list.append(member.id); await save_state(); await interaction.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="تنظيف", description="🗑️ حذف رسائل")
@discord.app_commands.describe(amount="العدد")
async def clear_cmd(interaction: discord.Interaction, amount: int):
    if not await require_control(interaction): return
    await interaction.response.defer(ephemeral=True)
    d = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"✅ {len(d)}", ephemeral=True)

# ═══════════════════════════════════════════════════════════════
# 🎬 التشغيل
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    log.info("البوت متصل: %s", bot.user)
    bot.add_view(TicketButtonView()); bot.add_view(CloseTicketButton()); bot.add_view(ApplicationButtonView())
    await load_all_state_async()
    try:
        guild = discord.Object(id=1475975508700303370)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info("تمت مزامنة الأوامر في سيرفرك بنجاح!")
    except Exception as e: log.error("فشل المزامنة: %s", e)
    
    try:
        import extras
        extras.load_extras(bot, {"apply_jail": apply_jail, "remove_jail": remove_jail, "require_control": require_control, "is_exempted": is_exempted})
    except: pass

if __name__ == "__main__":
    if TOKEN and TOKEN != "ضع_التوكن_هنا": bot.run(TOKEN)
