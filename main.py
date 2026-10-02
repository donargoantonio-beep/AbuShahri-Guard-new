"""
╔══════════════════════════════════════════════════════════╗
║  main.py — بوت إدارة وحماية متقدم                       ║
║  الإصدار: 4.0                                            ║
║  الميزات: Anti-Nuke، Anti-Role/Channel Delete،          ║
║          نسخ احتياطية، Rate Limiting، تحذير متدرج       ║
╚══════════════════════════════════════════════════════════╝
"""
import os
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

# keep_alive اختياري (لسيرفرات Replit)
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive():
        pass


# ==================== إعداد التسجيل ====================
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


# ==================== إنشاء المجلدات ====================
for d in [config.DATA_DIR, config.BACKUPS_DIR,
          config.ICONS_DIR, config.BANNERS_DIR, config.LOGS_DIR]:
    os.makedirs(d, exist_ok=True)


# ==================== النوايا ====================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.moderation = True

bot = commands.Bot(command_prefix="!nobotprefix!", intents=intents, help_command=None)


# ==================== الحالة العامة ====================
VOICE_CHANNEL_ID: int = 0
USER_WARNINGS: dict = {}
saved_roles: dict = {}
protected_users_list: list = []
protected_roles_list: list = []
deputy_user_ids: list = []
trusted_bots: list = []
SPAM_TRACKER: dict = {}
SPAM_CLEANUP_LAST = 0.0

# Anti-Nuke trackers: {guild_id: {user_id: {action: deque[timestamps]}}}
NUKE_TRACKER: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))

# سجل النيوكات لكل مستخدم: {guild_id: {user_id: count}}
NUKE_STRIKES: dict = defaultdict(lambda: defaultdict(int))

# Rate limiting: {user_id: {command: deque[timestamps]}}
RATE_LIMIT_TRACKER: dict = defaultdict(lambda: defaultdict(deque))


# ==================== أدوات JSON ====================

def _read_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"خطأ في قراءة {path}: {e}")
        return default


def _write_json(path: str, data) -> None:
    try:
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        log.error(f"خطأ في حفظ {path}: {e}")


async def async_save_json(path: str, data) -> None:
    await asyncio.to_thread(_write_json, path, data)


# ==================== البحث الذكي ====================

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


# ==================== اختصارات ====================

def get_role_jail(g):   return find_role(g, config.ROLE_JAIL)
def get_role_ticket(g): return find_role(g, config.ROLE_TICKET)
def get_role_apply(g):  return find_role(g, config.ROLE_APPLY)

def get_ch_admin_review(g):   return find_channel(g, config.CH_ADMIN_REVIEW, "text")
def get_ch_jail(g):           return find_channel(g, config.CH_JAIL, "text")
def get_ch_log_delete(g):     return find_channel(g, config.CH_LOG_DELETE, "text")
def get_ch_log_join_leave(g): return find_channel(g, config.CH_LOG_JOIN_LEAVE, "text")
def get_ch_log_ban(g):        return find_channel(g, config.CH_LOG_BAN, "text")
def get_ch_log_roles(g):      return find_channel(g, config.CH_LOG_ROLES, "text")
def get_ch_log_nickname(g):   return find_channel(g, config.CH_LOG_NICKNAME, "text")
def get_ch_log_timeout(g):    return find_channel(g, config.CH_LOG_TIMEOUT, "text")
def get_ch_log_nuke(g):       return find_channel(g, config.CH_LOG_NUKE, "text")
def get_ch_log_guild(g):      return find_channel(g, config.CH_LOG_GUILD, "text")
def get_ch_welcome(g):        return find_channel(g, config.CH_WELCOME, "text")
def get_ch_announce(g):       return find_channel(g, config.CH_ANNOUNCE, "text")
def get_ch_ticket_panel(g):   return find_channel(g, config.CH_TICKET_PANEL, "text")
def get_ch_apply_panel(g):    return find_channel(g, config.CH_APPLY_PANEL, "text")
def get_cat_ticket(g):        return find_channel(g, config.CH_TICKET_CATEGORY, "category")


# ==================== الحالة: تحميل وحفظ ====================

def load_all_state() -> None:
    global USER_WARNINGS, saved_roles, protected_users_list
    global protected_roles_list, deputy_user_ids, VOICE_CHANNEL_ID
    global trusted_bots, NUKE_STRIKES

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
        f"تم تحميل الحالة | تحذيرات={len(USER_WARNINGS)} | "
        f"محميون={len(protected_users_list)} | "
        f"رتب-محمية={len(protected_roles_list)} | "
        f"نواب={len(deputy_user_ids)} | "
        f"بوتات-موثوقة={len(trusted_bots)}"
    )


async def save_warnings() -> None:
    await async_save_json(
        config.WARNINGS_FILE,
        {str(k): v for k, v in USER_WARNINGS.items()}
    )


async def save_state() -> None:
    data = {
        "protected_users": protected_users_list,
        "protected_roles": protected_roles_list,
        "deputies": deputy_user_ids,
        "trusted_bots": trusted_bots,
        "voice_channel_id": VOICE_CHANNEL_ID,
        "saved_roles": {str(k): v for k, v in saved_roles.items()},
    }
    await async_save_json(config.STATE_FILE, data)


async def save_nuke_strikes() -> None:
    data = {str(gid): {str(uid): c for uid, c in users.items()}
            for gid, users in NUKE_STRIKES.items()}
    await async_save_json(config.ANTINUKE_FILE, data)


# ==================== تطبيع النص (للكلمات المحظورة) ====================

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


# ==================== الصلاحيات ====================

def is_owner(user_id: int) -> bool:
    return user_id == config.BOT_OWNER_ID


def is_deputy(user_id: int) -> bool:
    return user_id in deputy_user_ids


def has_control(user_id: int) -> bool:
    """المالك أو النائب"""
    return is_owner(user_id) or is_deputy(user_id)


def is_exempted(member: discord.Member) -> bool:
    """استثناء من كل الحمايات"""
    if not isinstance(member, discord.Member):
        return False
    if is_owner(member.id) or is_deputy(member.id):
        return True
    if member.guild and member.id == member.guild.owner_id:
        return True
    if member.id in protected_users_list:
        return True
    if member.bot and member.id in trusted_bots:
        return True
    protected_ids = set(protected_roles_list)
    return any(r.id in protected_ids for r in member.roles)


async def require_control(interaction: discord.Interaction) -> bool:
    """يتحقق أن المستخدم مالك أو نائب"""
    if has_control(interaction.user.id):
        return True
    if interaction.guild and interaction.user.id == interaction.guild.owner_id:
        return True
    await interaction.response.send_message(
        "❌ هذا الأمر مخصص لمالك البوت والنواب فقط.",
        ephemeral=True,
    )
    return False


async def require_owner(interaction: discord.Interaction) -> bool:
    """يتحقق أن المستخدم مالك فقط"""
    if is_owner(interaction.user.id):
        return True
    if interaction.guild and interaction.user.id == interaction.guild.owner_id:
        return True
    await interaction.response.send_message(
        "❌ هذا الأمر مخصص لمالك البوت فقط.",
        ephemeral=True,
    )
    return False


# ==================== فحص ترتيب الرتب ====================

def can_act_on(actor: discord.Member, target: discord.Member,
               guild: discord.Guild) -> tuple[bool, str]:
    """
    يتحقق أن البوت يقدر يعاقب target.
    يرجع (يمكن؟, سبب الفشل)
    """
    me = guild.me

    # البوت نفسه
    if target.id == me.id:
        return False, "❌ لا أستطيع معاقبة نفسي."

    # المالك
    if target.id == guild.owner_id:
        return False, "❌ لا يمكن معاقبة مالك السيرفر."

    # محمي
    if is_exempted(target):
        return False, "❌ هذا العضو محمي من الحمايات."

    # ترتيب الرتب: البوت لازم أعلى من الهدف
    if target.top_role >= me.top_role:
        return False, f"❌ رتبة {target.mention} أعلى أو تساوي رتبة البوت."

    # الفاعل لازم أعلى من الهدف (لو الفاعل عضو)
    if isinstance(actor, discord.Member) and actor.id != me.id:
        if not is_owner(actor.id) and not is_deputy(actor.id):
            if actor.guild and actor.id != actor.guild.owner_id:
                if target.top_role >= actor.top_role:
                    return False, "❌ لا تستطيع معاقبة عضو رتبته أعلى أو تساوي رتبتك."

    return True, ""


def bot_can_manage(target: Union[discord.Member, discord.Role],
                   guild: discord.Guild) -> tuple[bool, str]:
    """يتحقق أن البوت يقدر يعدل على الهدف"""
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


# ==================== Rate Limiting ====================

def check_rate_limit(user_id: int, command: str) -> tuple[bool, int]:
    """
    يفحص هل المستخدم تجاوز الحد.
    يرجع (مسموح؟, كم ثانية ينتظر)
    """
    if command not in config.RATE_LIMITS:
        return True, 0

    limit = config.RATE_LIMITS[command]
    max_calls = limit["max"]
    window = limit["window"]

    now = time.time()
    dq = RATE_LIMIT_TRACKER[user_id][command]

    # احذف القديم
    while dq and now - dq[0] > window:
        dq.popleft()

    if len(dq) >= max_calls:
        wait = int(window - (now - dq[0])) + 1
        return False, wait

    dq.append(now)
    return True, 0


# ==================== تنظيف SPAM_TRACKER ====================

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
# ============================================================
# 🚔 نظام الحجر الموحّد
# ============================================================

async def get_or_create_jail_channel(guild: discord.Guild,
                                     jail_role: discord.Role) -> Optional[discord.TextChannel]:
    """يرجع روم الحجر. لو ما لقاه، ينشئه كحل أخير."""
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
            log.warning("لم أجد روم الحجر — أنشأت واحد جديد.")
        except discord.Forbidden:
            log.error("لا أملك صلاحية إنشاء روم الحجر")
            return None
    else:
        try:
            await channel.set_permissions(
                jail_role, view_channel=True, send_messages=True, read_message_history=True
            )
            await channel.set_permissions(guild.default_role, view_channel=False)
        except Exception as e:
            log.warning(f"فشل تحديث صلاحيات روم الحجر: {e}")

    return channel


async def apply_jail(guild: discord.Guild, member: discord.Member,
                     reason: str) -> tuple[bool, str]:
    """
    يطبّق الحجر: يسحب الرتب، يعطيه رتبة محجور، يخرجه من الرومات الصوتية.
    يفحص ترتيب الرتب أولاً.
    """
    if is_exempted(member):
        return False, "❌ هذا العضو محمي، لا يمكن حجره."
    if not isinstance(member, discord.Member):
        return False, "❌ العضو غير موجود في السيرفر."

    # فحص ترتيب الرتب
    ok, why = bot_can_manage(member, guild)
    if not ok:
        return False, f"❌ لا أستطيع حجر {member.mention}: {why}"

    jail_role = get_role_jail(guild)
    if not jail_role:
        return False, "❌ لم أجد رتبة `محجور`. أضف آيديها في config.py."

    # فحص ترتيب رتبة المحجور نفسها
    if jail_role >= guild.me.top_role:
        return False, "❌ رتبة `محجور` أعلى من رتبة البوت. ارفع رتبة البوت فوقها."

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
        return True, "🔒 تم تطبيق الحجر بنجاح."
    except discord.Forbidden:
        return False, "❌ البوت لا يملك صلاحية تعديل رتب هذا العضو."
    except Exception as e:
        log.exception("خطأ في apply_jail")
        return False, f"❌ فشل الحجر: {e}"


async def remove_jail(guild: discord.Guild, member: discord.Member) -> tuple[bool, str]:
    """فك الحجر: يعيد الرتب المحفوظة، يمسح رتبة المحجور."""
    jail_role = get_role_jail(guild)
    if jail_role and jail_role in member.roles:
        try:
            await member.remove_roles(jail_role)
        except Exception as e:
            log.warning(f"فشل إزالة رتبة الحجر: {e}")

    if member.id in saved_roles:
        role_ids = saved_roles.pop(member.id)
        roles_to_restore = []
        for rid in role_ids:
            r = guild.get_role(rid)
            if r and r < guild.me.top_role:  # فحص الترتيب
                roles_to_restore.append(r)
        if roles_to_restore:
            try:
                await member.add_roles(*roles_to_restore, reason="فك الحجر")
            except Exception as e:
                log.warning(f"فشل استعادة الرتب: {e}")

    await save_state()
    return True, "🔓 تم فك الحجر واستعادة الرتب."


# ============================================================
# 🛡️ Anti-Nuke — النظام الكامل
# ============================================================

def _now() -> float:
    return time.time()


def _prune_deque(dq: deque, window: int):
    """يحذف العناصر القديمة من الطابور"""
    cutoff = _now() - window
    while dq and dq[0] < cutoff:
        dq.popleft()


def record_action(guild_id: int, user_id: int, action: str) -> int:
    """
    يسجّل عملية جديدة ويرجع عدد العمليات خلال الفترة المسموحة.
    """
    if action not in config.ANTI_NUKE_THRESHOLDS:
        return 0

    limit = config.ANTI_NUKE_THRESHOLDS[action]
    window = limit["seconds"]

    dq = NUKE_TRACKER[guild_id][user_id][action]
    dq.append(_now())
    _prune_deque(dq, window)
    return len(dq)


def is_nuke(guild_id: int, user_id: int, action: str) -> bool:
    """هل المستخدم تجاوز الحد؟"""
    if action not in config.ANTI_NUKE_THRESHOLDS:
        return False
    limit = config.ANTI_NUKE_THRESHOLDS[action]
    dq = NUKE_TRACKER[guild_id][user_id][action]
    _prune_deque(dq, limit["seconds"])
    return len(dq) > limit["count"]


def clear_user_tracker(guild_id: int, user_id: int, action: Optional[str] = None):
    """يمسح سجل عمليات المستخدم (بعد معاقبته)"""
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
                             limit: int = 5) -> Optional[discord.Member]:
    """يحاول معرفة من نفّذ العملية من audit log"""
    try:
        async for entry in guild.audit_logs(limit=limit, action=action):
            if entry.target and entry.target.id == target_id:
                # تحقق أن العملية حديثة (خلال 15 ثانية)
                age = (discord.utils.utcnow() - entry.created_at).total_seconds()
                if age < 15:
                    return entry.user
    except discord.Forbidden:
        log.warning("لا أملك صلاحية قراءة audit log")
    except Exception as e:
        log.warning(f"خطأ في audit log: {e}")
    return None


async def send_nuke_log(guild: discord.Guild, title: str, color: discord.Color,
                        fields: dict):
    """يرسل تقرير نيوك لروم اللوق"""
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


async def punish_nuker(guild: discord.Guild, member: discord.Member,
                       action: str, count: int) -> str:
    """
    يطبّق العقوبة بناءً على نظام التحذير المتدرج.
    - أول نيك: تحذير بالخاص
    - ثاني نيك: سحب رتب + حجر
    - ثالث نيك: بان نهائي
    """
    if member is None:
        return "❌ لم أعرف من نفّذ العملية."
    if member.id == guild.owner_id:
        return "❌ لا يمكن معاقبة مالك السيرفر."
    if is_exempted(member):
        return "⚠️ العضو محمي — لم تُطبَّق العقوبة."

    # زيادة عدّاد النيوكات
    NUKE_STRIKES[guild.id][member.id] += 1
    strikes = NUKE_STRIKES[guild.id][member.id]
    await save_nuke_strikes()

    reason = f"Anti-Nuke: {action} (المرة {strikes})"

    # تحذير متدرج
    if config.GRADUATED_NUKE_PUNISHMENT:
        if strikes == 1:
            try:
                await member.send(
                    f"⚠️ **تحذير أول — Anti-Nuke**\n"
                    f"تم كشف نشاط تخريبي منك في **{guild.name}**\n"
                    f"العملية: `{action}`\n"
                    f"عدد العمليات: `{count}`\n\n"
                    f"⚠️ **تحذير:** تكرار النشاط = سحب الرتب + حجر"
                )
            except Exception:
                pass
            return f"⚠️ تحذير أول لـ {member.mention} (نيك #1)"

        elif strikes == 2:
            ok, msg = await apply_jail(guild, member, reason)
            return f"🔒 حجر لـ {member.mention} (نيك #2) — {msg}"

        else:  # 3+
            try:
                await member.ban(reason=f"{reason} — نهائي", delete_message_days=0)
                return f"🔨 بان نهائي لـ {member.mention} (نيك #{strikes})"
            except Exception as e:
                return f"❌ فشل البان: {e}"

    # عقوبة عادية (بدون تدرج)
    if config.ANTI_NUKE_PUNISHMENT == "jail":
        ok, msg = await apply_jail(guild, member, reason)
        return f"🔒 {msg}"
    elif config.ANTI_NUKE_PUNISHMENT == "ban":
        try:
            await member.ban(reason=reason, delete_message_days=0)
            return f"🔨 بان {member.mention}"
        except Exception as e:
            return f"❌ فشل البان: {e}"

    return "✅ عُوقب"


async def handle_nuke_event(guild: discord.Guild, member: Optional[discord.Member],
                            action: str, target_desc: str,
                            restore_func=None):
    """
    المعالج المركزي لأي حدث نيوك.
    - يسجّل العملية
    - يفحص العتبة
    - لو تجاوز: يستعيد + يعاقب
    """
    if not config.ANTI_NUKE_ENABLED:
        return
    if member is None or member.bot and member.id in trusted_bots:
        return
    if member and is_exempted(member):
        return

    if not member:
        return

    count = record_action(guild.id, member.id, action)

    if not is_nuke(guild.id, member.id, action):
        return  # لسا ما تجاوز الحد

    # 🚨 نيك مكتشف!
    log.warning(f"🚨 NUKE detected: {member} → {action} × {count}")

    # استرجاع ما يمكن استرجاعه
    if restore_func:
        try:
            await restore_func()
        except Exception as e:
            log.exception(f"فشل الاسترجاع: {e}")

    # عقوبة
    punishment = await punish_nuker(guild, member, action, count)

    # لوق
    await send_nuke_log(
        guild,
        title="🚨 Anti-Nuke: تم كشف نشاط تخريبي",
        color=discord.Color.dark_red(),
        fields={
            "المخالف": f"{member.mention} (`{member.id}`)",
            "العملية": f"`{action}`",
            "عدد العمليات": f"**{count}** خلال {config.ANTI_NUKE_THRESHOLDS[action]['seconds']} ثانية",
            "الهدف": target_desc,
            "العقوبة": punishment,
        },
    )

    # امسح سجل عملياته
    clear_user_tracker(guild.id, member.id, action)


# ============================================================
# 📦 نظام النسخ الاحتياطية (اسم/أيقونة/بانر السيرفر)
# ============================================================

def _backup_meta_load() -> dict:
    return _read_json(config.BACKUP_FILE, {
        "names": [],
        "icons": [],
        "banners": [],
    })


def _backup_meta_save(data: dict) -> None:
    _write_json(config.BACKUP_FILE, data)


def _add_to_history(lst: list, value, max_len: int):
    """يضيف قيمة لقائمة مع منع التكرار والحد الأقصى"""
    if value in lst:
        lst.remove(value)
    lst.insert(0, value)
    del lst[max_len:]


def backup_guild_name(guild: discord.Guild):
    """يحفظ اسم السيرفر"""
    if not config.BACKUP_ENABLED:
        return
    meta = _backup_meta_load()
    _add_to_history(meta["names"], guild.name, 10)
    _backup_meta_save(meta)


async def backup_guild_icon(guild: discord.Guild):
    """يحفظ أيقونة السيرفر (الرابط + الملف محلياً)"""
    if not config.BACKUP_ENABLED:
        return
    if not guild.icon:
        return

    try:
        filename = f"{guild.id}_{int(_now())}.png"
        filepath = os.path.join(config.ICONS_DIR, filename)

        # تحميل الصورة
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

        # احذف الملفات القديمة الزائدة
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
        log.warning(f"فشل حفظ الأيقونة: {e}")


async def backup_guild_banner(guild: discord.Guild):
    """يحفظ بانر السيرفر"""
    if not config.BACKUP_ENABLED:
        return
    if not guild.banner:
        return

    try:
        filename = f"{guild.id}_{int(_now())}.png"
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
        log.warning(f"فشل حفظ البانر: {e}")


async def restore_guild_name(guild: discord.Guild,
                             save_current: bool = True) -> tuple[bool, str]:
    """يرجع آخر اسم محفوظ"""
    meta = _backup_meta_load()
    if len(meta["names"]) < 2:
        return False, "❌ لا يوجد اسم قديم محفوظ."

    previous = meta["names"][1]  # [0] هو الحالي

    try:
        if save_current:
            # احفظ الاسم الحالي قبل الرجوع
            pass
        await guild.edit(name=previous, reason="Anti-Nuke: استرجاع الاسم")
        return True, f"✅ تم استرجاع الاسم: `{previous}`"
    except discord.Forbidden:
        return False, "❌ لا أملك صلاحية تعديل اسم السيرفر."
    except Exception as e:
        return False, f"❌ فشل الاسترجاع: {e}"


async def restore_guild_icon(guild: discord.Guild) -> tuple[bool, str]:
    """يرجع آخر أيقونة محفوظة"""
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
        return False, f"❌ فشل الاسترجاع: {e}"


async def restore_guild_banner(guild: discord.Guild) -> tuple[bool, str]:
    """يرجع آخر بانر محفوظ"""
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
        return False, f"❌ فشل الاسترجاع: {e}"
# ============================================================
# 🗂️ Cache للرومات والرتب (لاسترجاعها عند الحذف)
# ============================================================

GUILD_CACHE_FILE = "data/guild_cache.json"
GUILD_CACHE: dict = defaultdict(lambda: {"channels": {}, "roles": {}})


def load_guild_cache():
    global GUILD_CACHE
    raw = _read_json(GUILD_CACHE_FILE, {})
    GUILD_CACHE = defaultdict(lambda: {"channels": {}, "roles": {}})
    for gid, data in raw.items():
        GUILD_CACHE[int(gid)] = {
            "channels": {int(k): v for k, v in data.get("channels", {}).items()},
            "roles": {int(k): v for k, v in data.get("roles", {}).items()},
        }


async def save_guild_cache():
    data = {str(gid): {
        "channels": {str(k): v for k, v in d["channels"].items()},
        "roles": {str(k): v for k, v in d["roles"].items()},
    } for gid, d in GUILD_CACHE.items()}
    await async_save_json(GUILD_CACHE_FILE, data)


def snapshot_channel(channel: discord.abc.GuildChannel) -> dict:
    """يأخذ لقطة من بيانات روم"""
    base = {
        "name": channel.name,
        "position": channel.position,
        "category_id": channel.category_id,
    }

    # overwrites
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
    """يأخذ لقطة من بيانات رتبة"""
    return {
        "name": role.name,
        "color": role.color.value,
        "permissions": role.permissions.value,
        "position": role.position,
        "hoist": role.hoist,
        "mentionable": role.mentionable,
        "unicode_emoji": role.unicode_emoji,
        "icon_url": role.icon.url if role.icon else None,
        "is_bot_managed": role.is_bot_managed(),
        "is_premium": role.is_premium_subscriber(),
    }


def rebuild_overwrites(guild: discord.Guild, overwrites_data: dict) -> dict:
    """يعيد بناء Overwrites من البيانات"""
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
    """يأخذ لقطة كاملة من السيرفر عند البدء"""
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
    log.info(f"📸 لقطة كاملة للسيرفر: {guild.name} ({len(channels_data)} روم، {len(roles_data)} رتبة)")


async def restore_channel_from_cache(guild: discord.Guild, ch_id: int) -> Optional[discord.abc.GuildChannel]:
    """يعيد إنشاء روم محذوف من الـ cache"""
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

        # حدّث الـ cache بالآيدي الجديد
        cache["channels"][new_ch.id] = snapshot_channel(new_ch)
        if ch_id in cache["channels"]:
            del cache["channels"][ch_id]
        await save_guild_cache()
        return new_ch
    except Exception as e:
        log.exception(f"فشل استرجاع الروم: {e}")
        return None


async def restore_role_from_cache(guild: discord.Guild, role_id: int) -> Optional[discord.Role]:
    """يعيد إنشاء رتبة محذوفة من الـ cache"""
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
        # حاول رفعها للموضع الأصلي
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
        log.exception(f"فشل استرجاع الرتبة: {e}")
        return None


# ============================================================
# 🚨 Events — Anti-Nuke
# ============================================================

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    await asyncio.sleep(0.7)

    # امسحه من الـ cache
    cache = GUILD_CACHE.get(guild.id, {})
    cached_data = cache.get("channels", {}).get(channel.id, snapshot_channel(channel))

    # احفظ اللقطة قبل الحذف (channel object لسا موجود)
    GUILD_CACHE[guild.id]["channels"][channel.id] = cached_data
    await save_guild_cache()

    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_delete, channel.id)

    # لو البوت نفسه أو محمي
    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        # استرجاع بدون عقوبة
        await restore_channel_from_cache(guild, channel.id)
        return

    # استرجع الروم فوراً (بغض النظر عن العتبة)
    await restore_channel_from_cache(guild, channel.id)

    # سجّل العملية
    if executor:
        await handle_nuke_event(
            guild, executor, "channel_delete",
            f"`{channel.name}` ({channel.id})",
        )
    else:
        await send_nuke_log(
            guild, "⚠️ حذف روم (بدون معرفة الفاعل)",
            discord.Color.orange(),
            {"الروم المحذوف": f"`{channel.name}`", "ملاحظة": "لم أتمكن من قراءة audit log"},
        )


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    guild = channel.guild

    # حدّث الـ cache
    GUILD_CACHE[guild.id]["channels"][channel.id] = snapshot_channel(channel)
    await save_guild_cache()

    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_create, channel.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    if executor:
        await handle_nuke_event(
            guild, executor, "channel_create",
            f"`{channel.name}` ({channel.id})",
            restore_func=lambda: channel.delete(reason="Anti-Nuke: حذف روم مُنشأ"),
        )


@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel,
                                  after: discord.abc.GuildChannel):
    guild = after.guild

    # حدّث الـ cache
    GUILD_CACHE[guild.id]["channels"][after.id] = snapshot_channel(after)
    await save_guild_cache()

    # لوق تعديل الرومات (فقط التغييرات المهمة)
    changes = []
    if before.name != after.name:
        changes.append(f"الاسم: `{before.name}` → `{after.name}`")
    if isinstance(before, discord.TextChannel) and before.topic != after.topic:
        changes.append(f"الموضوع تغيّر")
    if before.category_id != after.category_id:
        changes.append(f"القسم تغيّر")

    if changes:
        log_ch = get_ch_log_guild(guild)
        if log_ch:
            executor = await get_audit_executor(guild, discord.AuditLogAction.channel_update, after.id)
            embed = discord.Embed(
                title="✏️ تعديل روم",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(name="الروم", value=after.mention, inline=False)
            embed.add_field(name="التغييرات", value="\n".join(changes), inline=False)
            if executor:
                embed.add_field(name="بواسطة", value=executor.mention, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.channel_update, after.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    if executor:
        await handle_nuke_event(
            guild, executor, "channel_update",
            f"`{after.name}`",
        )


@bot.event
async def on_guild_role_delete(role: discord.Role):
    guild = role.guild

    if role.is_default() or role.managed:
        return

    # احفظ اللقطة
    GUILD_CACHE[guild.id]["roles"][role.id] = snapshot_role(role)
    await save_guild_cache()

    await asyncio.sleep(0.7)
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_delete, role.id)

    # استرجع الرتبة
    await restore_role_from_cache(guild, role.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    # لوق
    log_ch = get_ch_log_roles(guild)
    if log_ch:
        embed = discord.Embed(title="🗑️ حذف رتبة",
                              color=discord.Color.dark_red(),
                              timestamp=discord.utils.utcnow())
        embed.add_field(name="الرتبة", value=f"`{role.name}`", inline=False)
        if executor:
            embed.add_field(name="بواسطة", value=executor.mention, inline=False)
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    if executor:
        await handle_nuke_event(
            guild, executor, "role_delete",
            f"`{role.name}`",
        )


@bot.event
async def on_guild_role_create(role: discord.Role):
    guild = role.guild

    if role.managed:
        return

    GUILD_CACHE[guild.id]["roles"][role.id] = snapshot_role(role)
    await save_guild_cache()

    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_create, role.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    if executor:
        await handle_nuke_event(
            guild, executor, "role_create",
            f"`{role.name}`",
            restore_func=lambda: role.delete(reason="Anti-Nuke: حذف رتبة مُنشأة"),
        )


@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role):
    guild = after.guild

    if after.is_default() or after.managed:
        return

    # فحص الصلاحيات
    if before.permissions != after.permissions:
        # رتبة محمية؟ استرجع
        if after.id in protected_roles_list:
            try:
                await after.edit(
                    permissions=before.permissions,
                    reason="Anti-Nuke: إرجاع صلاحيات رتبة محمية",
                )
            except Exception as e:
                log.warning(f"فشل إرجاع الرتبة المحمية: {e}")

            # لوق
            log_ch = get_ch_log_roles(guild)
            if log_ch:
                embed = discord.Embed(title="🛡️ محاولة تعديل رتبة محمية",
                                      color=discord.Color.red(),
                                      timestamp=discord.utils.utcnow())
                embed.add_field(name="الرتبة", value=after.mention, inline=False)
                executor = await get_audit_executor(guild, discord.AuditLogAction.role_update, after.id)
                if executor:
                    embed.add_field(name="بواسطة", value=executor.mention, inline=False)
                await log_ch.send(embed=embed)

    # لوق التعديلات
    changes = []
    if before.name != after.name:
        changes.append(f"الاسم: `{before.name}` → `{after.name}`")
    if before.color != after.color:
        changes.append(f"اللون: `{before.color}` → `{after.color}`")
    if before.permissions != after.permissions:
        changes.append("الصلاحيات تغيّرت")
    if before.hoist != after.hoist:
        changes.append(f"Hoist: `{before.hoist}` → `{after.hoist}`")

    if changes:
        log_ch = get_ch_log_roles(guild)
        if log_ch:
            executor = await get_audit_executor(guild, discord.AuditLogAction.role_update, after.id)
            embed = discord.Embed(title="✏️ تعديل رتبة",
                                  color=discord.Color.blue(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="الرتبة", value=after.mention, inline=False)
            embed.add_field(name="التغييرات", value="\n".join(changes), inline=False)
            if executor:
                embed.add_field(name="بواسطة", value=executor.mention, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

    # حدّث الـ cache
    GUILD_CACHE[guild.id]["roles"][after.id] = snapshot_role(after)
    await save_guild_cache()

    await asyncio.sleep(0.5)
    executor = await get_audit_executor(guild, discord.AuditLogAction.role_update, after.id)

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    if executor:
        await handle_nuke_event(
            guild, executor, "role_update",
            f"`{after.name}`",
        )


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    await asyncio.sleep(0.7)
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban, user.id)

    # لوق الباند
    log_ch = get_ch_log_ban(guild)
    if log_ch:
        embed = discord.Embed(title="🔨 حظر عضو",
                              color=discord.Color.dark_magenta(),
                              timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=f"{user.mention} (`{user.id}`)", inline=False)
        if executor:
            embed.add_field(name="بواسطة", value=executor.mention, inline=False)
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass

    if executor and (executor.id == bot.user.id or is_exempted(executor)):
        return

    if executor:
        async def unban():
            try:
                await guild.unban(user, reason="Anti-Nuke: إلغاء بان تخريبي")
                log.info(f"تم فك البان عن {user}")
            except Exception as e:
                log.warning(f"فشل فك البان: {e}")

        await handle_nuke_event(
            guild, executor, "ban",
            f"{user.mention} (`{user.id}`)",
            restore_func=unban,
        )


@bot.event
async def on_member_remove(member: discord.Member):
    guild = member.guild

    # تجاهل إذا كان بان (on_member_ban يشتغل قبل هذا أحياناً)
    await asyncio.sleep(1.0)

    executor = await get_audit_executor(guild, discord.AuditLogAction.kick, member.id)

    if executor:
        # هذا كيك وليس مغادرة عادية

        # لوق الكيك
        log_ch = get_ch_log_ban(guild)
        if log_ch:
            embed = discord.Embed(title="👞 طرد عضو (Kick)",
                                  color=discord.Color.orange(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="بواسطة", value=executor.mention, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        if executor.id == bot.user.id or is_exempted(executor):
            return

        # محاولة إرسال دعوة للعضو المطروود
        async def reinvite():
            try:
                await member.send(
                    f"⚠️ تم طردك من **{guild.name}** بشكل تخريبي.\n"
                    f"البوت حاول حمايتك.\n"
                    f"يمكنك العودة عبر رابط الدعوة إن كان متاحاً."
                )
            except Exception:
                pass

        await handle_nuke_event(
            guild, executor, "kick",
            f"{member.mention} (`{member.id}`)",
            restore_func=reinvite,
        )
        return

    # مغادرة عادية — لوق الدخول/الخروج
    log_ch = get_ch_log_join_leave(guild)
    if log_ch:
        embed = discord.Embed(title="📤 عضو غادر",
                              color=discord.Color.orange(),
                              timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass


@bot.event
async def on_audit_log_entry_create(entry: discord.AuditLogEntry):
    """يستخدم لكشف إضافة البوتات والـ Webhooks"""
    guild = entry.guild

    # كشف إضافة بوت
    if entry.action == discord.AuditLogAction.bot_add:
        target = entry.target
        if not isinstance(target, discord.Member):
            return
        if is_exempted(entry.user):
            return

        # لوق
        log_ch = get_ch_log_guild(guild) or get_ch_admin_review(guild)
        if log_ch:
            embed = discord.Embed(title="🤖 إضافة بوت",
                                  color=discord.Color.purple(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="البوت", value=f"{target.mention} (`{target.id}`)", inline=False)
            embed.add_field(name="بواسطة", value=entry.user.mention, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        # لو البوت غير موثوق، اطرده + عاقب اللي أضافه
        if target.id not in trusted_bots:
            try:
                await target.kick(reason="Anti-Nuke: بوت غير موثوق")
            except Exception:
                pass

            await handle_nuke_event(
                guild, entry.user, "bot_add",
                f"{target} (`{target.id}`)",
            )

    # كشف إنشاء Webhook
    elif entry.action == discord.AuditLogAction.webhook_create:
        if is_exempted(entry.user):
            return

        log_ch = get_ch_log_guild(guild) or get_ch_admin_review(guild)
        if log_ch:
            embed = discord.Embed(title="🔗 إنشاء Webhook",
                                  color=discord.Color.orange(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="القناة", value=entry.target, inline=False)
            embed.add_field(name="بواسطة", value=entry.user.mention, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        # حاول حذف الـ webhook
        async def del_webhook():
            try:
                webhooks = await entry.target.webhooks()
                for wh in webhooks:
                    if wh.user and wh.user.id == entry.user.id:
                        await wh.delete(reason="Anti-Nuke: webhook مشبوه")
            except Exception:
                pass

        await handle_nuke_event(
            guild, entry.user, "webhook_create",
            f"في {entry.target}",
            restore_func=del_webhook,
        )


# ============================================================
# 🏰 حماية السيرفر (اسم/أيقونة/بانر)
# ============================================================

@bot.event
async def on_guild_update(before: discord.Guild, after: discord.Guild):
    guild = after

    # اسم السيرفر
    if before.name != after.name:
        log_ch = get_ch_log_guild(guild)
        if log_ch:
            embed = discord.Embed(title="📝 تغيير اسم السيرفر",
                                  color=discord.Color.blue(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="القديم", value=f"`{before.name}`", inline=True)
            embed.add_field(name="الجديد", value=f"`{after.name}`", inline=True)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        await asyncio.sleep(1)
        executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update, guild.id)

        if executor and not is_exempted(executor) and executor.id != bot.user.id:
            # احفظ الاسم القديم قبل الرجوع
            ok, msg = await restore_guild_name(guild)
            if ok:
                await send_nuke_log(guild, "🛡️ استرجاع اسم السيرفر",
                                    discord.Color.green(),
                                    {"الاسم الأصلي": f"`{before.name}`",
                                     "بواسطة": executor.mention})

    # أيقونة السيرفر
    if before.icon != after.icon:
        # احفظ الأيقونة الجديدة إن كانت موجودة، لكن قبل ما نرجّع القديمة
        # الأفضل نحفظ القديمة أولاً قبل ما تنحذف — نستخدم اللقطة المخزنة

        log_ch = get_ch_log_guild(guild)
        if log_ch:
            embed = discord.Embed(title="🖼️ تغيير أيقونة السيرفر",
                                  color=discord.Color.blue(),
                                  timestamp=discord.utils.utcnow())
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        # حاول استرجاع الأيقونة القديمة
        await asyncio.sleep(1)
        executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update, guild.id)
        if executor and not is_exempted(executor) and executor.id != bot.user.id:
            ok, msg = await restore_guild_icon(guild)
            if ok:
                await send_nuke_log(guild, "🛡️ استرجاع أيقونة السيرفر",
                                    discord.Color.green(),
                                    {"بواسطة": executor.mention})

    # بانر السيرفر
    if before.banner != after.banner:
        log_ch = get_ch_log_guild(guild)
        if log_ch:
            embed = discord.Embed(title="🖼️ تغيير بانر السيرفر",
                                  color=discord.Color.blue(),
                                  timestamp=discord.utils.utcnow())
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

        await asyncio.sleep(1)
        executor = await get_audit_executor(guild, discord.AuditLogAction.guild_update, guild.id)
        if executor and not is_exempted(executor) and executor.id != bot.user.id:
            ok, msg = await restore_guild_banner(guild)
            if ok:
                await send_nuke_log(guild, "🛡️ استرجاع بانر السيرفر",
                                    discord.Color.green(),
                                    {"بواسطة": executor.mention})


# ============================================================
# 👋 الترحيب والرسائل واللوقات العادية
# ============================================================

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild

    # ترحيب بالخاص
    try:
        invite_url = None
        try:
            invites = await guild.invites()
            if invites:
                invite_url = invites[0].url
        except Exception:
            pass

        dm_embed = discord.Embed(
            title=f"سيرفر {guild.name}⛅ | - نرجو الالتزام -",
            description=config.RULES_TEXT,
            color=discord.Color.blurple(),
        )
        view = View()
        if invite_url:
            view.add_item(Button(label=f"سيرفر {guild.name}", url=invite_url,
                                 style=discord.ButtonStyle.link))
            await member.send(embed=dm_embed, view=view)
        else:
            await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass
    except Exception as e:
        log.warning(f"فشل إرسال الترحيب: {e}")

    # روم الترحيب
    welcome_ch = get_ch_welcome(guild)
    if welcome_ch:
        embed = discord.Embed(
            title="🎉 عضو جديد!",
            description=f"مرحباً {member.mention} في **{guild.name}**!\nنتمنى لك وقتاً ممتعاً.",
            color=discord.Color.brand_green(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await welcome_ch.send(content=member.mention, embed=embed)
        except Exception:
            pass

    # لوق الدخول
    log_ch = get_ch_log_join_leave(guild)
    if log_ch:
        embed = discord.Embed(title="📥 عضو انضم",
                              color=discord.Color.green(),
                              timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.set_footer(text=f"عدد الأعضاء: {guild.member_count}")
        try:
            await log_ch.send(embed=embed)
        except Exception:
            pass


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # تغيير الرتب
    if before.roles != after.roles:
        log_ch = get_ch_log_roles(after.guild)
        if log_ch:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]
            embed = discord.Embed(title="👑 تحديث رتب",
                                  color=discord.Color.blue(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=after.mention, inline=False)
            if added:
                embed.add_field(name="🟢 أُضيفت",
                                value=", ".join(r.mention for r in added)[:1024],
                                inline=False)
            if removed:
                embed.add_field(name="🔴 أُزيلت",
                                value=", ".join(r.mention for r in removed)[:1024],
                                inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass

    # تغيير اللقب
    if before.nick != after.nick:
        log_ch = get_ch_log_nickname(after.guild)
        if log_ch:
            embed = discord.Embed(title="✏️ تغيّر اللقب",
                                  color=discord.Color.gold(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=after.mention, inline=False)
            embed.add_field(name="القديم", value=before.nick or "—", inline=True)
            embed.add_field(name="الجديد", value=after.nick or "—", inline=True)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    log_ch = get_ch_log_delete(message.guild)
    if not log_ch:
        return
    embed = discord.Embed(title="🗑️ حذف رسالة",
                          color=discord.Color.dark_red(),
                          timestamp=discord.utils.utcnow())
    embed.add_field(name="صاحب الرسالة", value=message.author.mention, inline=True)
    embed.add_field(name="الروم", value=message.channel.mention, inline=True)
    embed.add_field(name="المحتوى",
                    value=(message.content or "*(وسائط)*")[:1000],
                    inline=False)
    try:
        await log_ch.send(embed=embed)
    except Exception:
        pass


# ============================================================
# 💬 نظام كشف المخالفات (سب/روابط/سبام)
# ============================================================

def detect_violation(message: discord.Message) -> Optional[str]:
    raw = message.content or ""

    if message.mention_everyone:
        return "منشن الجميع (@everyone / @here)"

    _, cleaned, collapsed = normalize_text(raw)
    if BAD_WORDS_RE.search(cleaned) or BAD_WORDS_RE.search(collapsed):
        return "السب والشتم / ألفاظ نابية"

    if URL_REGEX.search(raw):
        return "إرسال روابط أو دعوات سيرفرات"

    user_id = message.author.id
    now = time.time()
    entry = SPAM_TRACKER.get(user_id)
    if entry:
        last_text, last_time, count = entry
        if raw == last_text and (now - last_time) < 3:
            count += 1
            if count >= 2:
                SPAM_TRACKER[user_id] = (raw, now, count)
                return "السبام وتكرار الرسائل"
            SPAM_TRACKER[user_id] = (raw, now, count)
        else:
            SPAM_TRACKER[user_id] = (raw, now, 1)
    else:
        SPAM_TRACKER[user_id] = (raw, now, 1)

    return None


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if message.content.startswith(bot.command_prefix):
        await bot.process_commands(message)
        return

    if is_exempted(message.author):
        return

    cleanup_spam_tracker()
    violation = detect_violation(message)
    if not violation:
        return

    guild = message.guild
    member = message.author

    try:
        await message.delete()
    except Exception:
        pass

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    USER_WARNINGS.setdefault(member.id, []).append({
        "reason": violation,
        "warned_by": "النظام التلقائي 🤖",
        "date": now_str,
    })
    warn_count = len(USER_WARNINGS[member.id])

    action_taken = ""

    if violation == "السب والشتم / ألفاظ نابية":
        ok, msg = await apply_jail(guild, member, f"مخالفة: {violation}")
        action_taken = f"{msg} (حجر فوري)"
    else:
        try:
            until = discord.utils.utcnow() + datetime.timedelta(hours=1)
            await member.timeout(until, reason=f"تحذير {warn_count}: {violation}")
            action_taken = f"⚠️ تحذير رقم {warn_count} + ⏱️ تايم آوت ساعة."
        except discord.Forbidden:
            action_taken = f"⚠️ تحذير رقم {warn_count} (فشل التايم آوت)."
        except Exception as e:
            action_taken = f"⚠️ تحذير رقم {warn_count} (فشل: {e})"

        if warn_count >= 3:
            ok, msg = await apply_jail(guild, member, f"بلوغ {warn_count} تحذيرات")
            action_taken += f"\n{msg}"

    await save_warnings()

    try:
        await member.send(
            f"⚠️ **تنبيه إداري من سيرفر {guild.name}**\n"
            f"• **المخالفة:** {violation}\n"
            f"• **الإجراء:** {action_taken}\n"
            f"• **إجمالي تحذيراتك:** {warn_count}"
        )
    except Exception:
        pass

    admin_ch = get_ch_admin_review(guild)
    if admin_ch:
        embed = discord.Embed(title="🚨 رصد مخالفة",
                              color=discord.Color.red(),
                              timestamp=discord.utils.utcnow())
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="الروم", value=message.channel.mention, inline=True)
        embed.add_field(name="المخالفة", value=violation, inline=True)
        embed.add_field(name="التحذيرات", value=f"**{warn_count}**", inline=True)
        embed.add_field(name="الإجراء", value=action_taken, inline=False)
        content = (message.content or "")[:1000] or "*(وسائط فقط)*"
        embed.add_field(name="الرسالة", value=f"`{content}`", inline=False)
        try:
            await admin_ch.send(embed=embed)
        except Exception:
            pass


@bot.event
async def on_voice_state_update(member: discord.Member,
                                before: discord.VoiceState,
                                after: discord.VoiceState):
    # طرد المحجورين من الرومات الصوتية
    jail_role = get_role_jail(member.guild)
    if jail_role and jail_role in member.roles and after.channel is not None:
        try:
            await member.move_to(None)
        except Exception:
            pass
        return

    # إعادة اتصال البوت
    if VOICE_CHANNEL_ID == 0 or member.id != bot.user.id:
        return
    if before.channel and before.channel.id == VOICE_CHANNEL_ID:
        if after.channel is None or after.channel.id != VOICE_CHANNEL_ID:
            await asyncio.sleep(2)
            channel = member.guild.get_channel(VOICE_CHANNEL_ID)
            if isinstance(channel, discord.VoiceChannel):
                try:
                    if member.guild.me.voice:
                        try:
                            await member.guild.me.voice.disconnect()
                        except Exception:
                            pass
                    await channel.connect()
                except Exception as e:
                    log.warning(f"فشل إعادة الاتصال الصوتي: {e}")


# ============================================================
# 🎫 الواجهات (Views/Modals)
# ============================================================

class ApplicationModal(Modal, title="نموذج التقديم للإدارة"):
    q1 = TextInput(label="الاسم", placeholder="اكتب اسمك...", required=True, max_length=100)
    q2 = TextInput(label="العمر", placeholder="اكتب عمرك...", required=True, max_length=10)
    q3 = TextInput(label="سبب الانضمام", style=discord.TextStyle.paragraph,
                   placeholder="اكتب السبب...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        admin_ch = get_ch_admin_review(interaction.guild)
        if not admin_ch:
            await interaction.response.send_message(
                "❌ لم أجد روم `admin-review`.", ephemeral=True
            )
            return

        embed = discord.Embed(title="📥 طلب تقديم جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.name,
                         icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="المتقدم", value=interaction.user.mention, inline=False)
        embed.add_field(name="الاسم", value=self.q1.value, inline=False)
        embed.add_field(name="العمر", value=self.q2.value, inline=False)
        embed.add_field(name="السبب", value=self.q3.value, inline=False)

        await admin_ch.send(embed=embed, view=AdminDecisionView(member=interaction.user))
        await interaction.response.send_message("✅ تم إرسال تقديمك للإدارة!", ephemeral=True)


class ApplicationButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تقديم على الإدارة", style=discord.ButtonStyle.green,
                       custom_id="apply_button_permanent_v4")
    async def apply_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModal())


class AdminDecisionView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    async def _check_perm(self, interaction: discord.Interaction) -> bool:
        role = get_role_apply(interaction.guild)
        if (role and role in interaction.user.roles) or has_control(interaction.user.id):
            return True
        await interaction.response.send_message("❌ لا تمتلك الصلاحية.", ephemeral=True)
        return False

    @discord.ui.button(label="قبول", style=discord.ButtonStyle.blurple,
                       custom_id="accept_app_btn_v4")
    async def accept_app(self, interaction: discord.Interaction, button: Button):
        if not await self._check_perm(interaction):
            return
        try:
            await self.member.send("🎉 مبروك! تم قبول طلب تقديمك.")
        except Exception:
            pass
        await interaction.message.edit(view=None)
        await interaction.response.send_message(
            f"✅ تم قبول طلب {self.member.mention}.", ephemeral=True
        )

    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red,
                       custom_id="reject_app_btn_v4")
    async def reject_app(self, interaction: discord.Interaction, button: Button):
        if not await self._check_perm(interaction):
            return
        try:
            await self.member.send("❌ نأسف، تم رفض طلب تقديمك.")
        except Exception:
            pass
        await interaction.message.edit(view=None)
        await interaction.response.send_message(
            f"❌ تم رفض طلب {self.member.mention}.", ephemeral=True
        )


class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red,
                       custom_id="close_ticket_btn_v4")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        role = get_role_ticket(interaction.guild)
        if not ((role and role in interaction.user.roles) or has_control(interaction.user.id)):
            await interaction.response.send_message("❌ لا تمتلك الصلاحية.", ephemeral=True)
            return
        await interaction.response.send_message("⏳ سيتم حذف التذكرة خلال ثانيتين...", ephemeral=True)
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة 🎫", style=discord.ButtonStyle.primary,
                       custom_id="open_ticket_btn_v4")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = get_cat_ticket(guild)
        if not category:
            await interaction.response.send_message(
                "❌ لم أجد تصنيف `التذاكر`. أنشئه أو أضف آيديه في config.py.",
                ephemeral=True,
            )
            return

        # ⭐ استخدام ID العضو في اسم التذكرة (يمنع فتح أكثر من تذكرة بتغيير الاسم)
        channel_name = f"ticket-{interaction.user.id}"

        # ⭐ فحص قوي: ابحث عن أي تذكرة فيها آيدي المستخدم
        existing = None
        for ch in category.text_channels:
            if ch.name == channel_name or str(interaction.user.id) in ch.name:
                # تأكد أن المستخدم لا يزال عنده صلاحية الوصول
                if ch.permissions_for(interaction.user).view_channel:
                    existing = ch
                    break

        if existing:
            await interaction.response.send_message(
                f"❌ لديك تذكرة مفتوحة: {existing.mention}", ephemeral=True
            )
            return

        ticket_role = get_role_ticket(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if ticket_role:
            overwrites[ticket_role] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )

        try:
            ch = await guild.create_text_channel(channel_name, category=category,
                                                 overwrites=overwrites)
        except Exception as e:
            await interaction.response.send_message(f"❌ فشل إنشاء التذكرة: {e}", ephemeral=True)
            return

        embed = discord.Embed(
            title="تذكرة جديدة",
            description="اكتب مشكلتك وسيتم الرد عليك قريباً.",
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"صاحب التذكرة: {interaction.user} ({interaction.user.id})")

        await ch.send(content=interaction.user.mention, embed=embed, view=CloseTicketButton())
        await interaction.response.send_message(
            f"✅ تم فتح تذكرتك: {ch.mention}", ephemeral=True
        )
# ============================================================
# 🎯 الأوامر — إدارة عامة
# ============================================================

@bot.tree.command(name="فحص_الاعدادات",
                  description="يفحص وجود جميع الرومات والرتب ويرشدك للناقص")
async def check_setup(interaction: discord.Interaction):
    if not await require_control(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    results = []
    missing = []

    role_checks = [
        ("رتبة المحجور", get_role_jail(guild), config.ROLE_JAIL),
        ("رتبة مسؤول التذاكر", get_role_ticket(guild), config.ROLE_TICKET),
        ("رتبة مسؤول التقديم", get_role_apply(guild), config.ROLE_APPLY),
    ]
    for label, found, cfg in role_checks:
        if found:
            results.append(f"✅ **{label}**: {found.mention} (`{found.id}`)")
        else:
            results.append(f"❌ **{label}**: غير موجود")
            missing.append(f"رتبة: {' / '.join(cfg['names'])}")

    channel_checks = [
        ("روم admin-review", get_ch_admin_review(guild), config.CH_ADMIN_REVIEW),
        ("روم الحجر", get_ch_jail(guild), config.CH_JAIL),
        ("لوق الحذف", get_ch_log_delete(guild), config.CH_LOG_DELETE),
        ("لوق دخول/خروج", get_ch_log_join_leave(guild), config.CH_LOG_JOIN_LEAVE),
        ("لوق الطرد", get_ch_log_ban(guild), config.CH_LOG_BAN),
        ("لوق الرتب", get_ch_log_roles(guild), config.CH_LOG_ROLES),
        ("لوق اللقب", get_ch_log_nickname(guild), config.CH_LOG_NICKNAME),
        ("لوق النيوك", get_ch_log_nuke(guild), config.CH_LOG_NUKE),
        ("لوق حماية السيرفر", get_ch_log_guild(guild), config.CH_LOG_GUILD),
        ("روم الترحيب", get_ch_welcome(guild), config.CH_WELCOME),
        ("روم الإعلانات", get_ch_announce(guild), config.CH_ANNOUNCE),
        ("تصنيف التذاكر", get_cat_ticket(guild), config.CH_TICKET_CATEGORY),
    ]
    for label, found, cfg in channel_checks:
        if found:
            results.append(f"✅ **{label}**: {found.mention} (`{found.id}`)")
        else:
            results.append(f"❌ **{label}**: غير موجود")
            missing.append(f"روم: {' / '.join(cfg['names'])}")

    embed = discord.Embed(
        title="🔍 تقرير فحص الإعدادات",
        description="\n".join(results[:25]),
        color=discord.Color.blue() if not missing else discord.Color.orange(),
    )

    if missing:
        embed.add_field(
            name="⚠️ ناقص",
            value="\n".join(f"• {m}" for m in missing[:10]),
            inline=False,
        )
        embed.set_footer(text="💡 أضف الآيدي مباشرة في config.py")
    else:
        embed.add_field(name="✅", value="كل الإعدادات جاهزة!", inline=False)

    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="اختبار_الحماية",
                  description="فحص شامل لكل أنظمة الحماية")
async def test_protection(interaction: discord.Interaction):
    if not await require_control(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    me = guild.me

    checks = []

    # صلاحيات البوت
    perms_needed = [
        ("manage_roles", "إدارة الرتب"),
        ("manage_channels", "إدارة الرومات"),
        ("kick_members", "طرد الأعضاء"),
        ("ban_members", "حظر الأعضاء"),
        ("manage_guild", "إدارة السيرفر"),
        ("moderate_members", "تايم آوت الأعضاء"),
        ("view_audit_log", "قراءة Audit Log"),
        ("manage_webhooks", "إدارة Webhooks"),
    ]
    for perm, label in perms_needed:
        if getattr(me.guild_permissions, perm, False):
            checks.append(f"✅ صلاحية: **{label}**")
        else:
            checks.append(f"❌ صلاحية ناقصة: **{label}**")

    # ترتيب رتبة البوت
    jail_role = get_role_jail(guild)
    if jail_role:
        if jail_role < me.top_role:
            checks.append(f"✅ رتبة البوت أعلى من رتبة `{jail_role.name}`")
        else:
            checks.append(f"❌ رتبة البوت ليست أعلى من `{jail_role.name}`")

    # الـ cache
    cache = GUILD_CACHE.get(guild.id, {})
    ch_count = len(cache.get("channels", {}))
    rl_count = len(cache.get("roles", {}))
    checks.append(f"📦 Cache: **{ch_count}** روم / **{rl_count}** رتبة")

    # Anti-Nuke
    if config.ANTI_NUKE_ENABLED:
        checks.append(f"✅ Anti-Nuke: **مفعّل** ({len(config.ANTI_NUKE_THRESHOLDS)} حدث مراقب)")
    else:
        checks.append("⚠️ Anti-Nuke: **معطّل**")

    # اللوقات
    log_missing = []
    for label, ch in [
        ("النيوك", get_ch_log_nuke(guild)),
        ("حماية السيرفر", get_ch_log_guild(guild)),
    ]:
        if not ch:
            log_missing.append(label)
    if log_missing:
        checks.append(f"⚠️ لوقات ناقصة: {', '.join(log_missing)}")
    else:
        checks.append("✅ كل اللوقات الجديدة موجودة")

    embed = discord.Embed(
        title="🧪 اختبار الحماية",
        description="\n".join(checks[:25]),
        color=discord.Color.green(),
    )
    await interaction.followup.send(embed=embed, ephemeral=True)


# ============================================================
# 🎯 الأوامر — العقوبات
# ============================================================

@bot.tree.command(name="طرد", description="طرد عضو")
@discord.app_commands.describe(member="العضو", reason="السبب")
async def kick_cmd(interaction: discord.Interaction, member: discord.Member,
                   reason: str = "لم يُحدد"):
    if not await require_control(interaction):
        return
    allowed, wait = check_rate_limit(interaction.user.id, "طرد")
    if not allowed:
        await interaction.response.send_message(f"⏱️ تجاوزت الحد. انتظر {wait} ثانية.", ephemeral=True)
        return

    ok, why = can_act_on(interaction.user, member, interaction.guild)
    if not ok:
        await interaction.response.send_message(why, ephemeral=True)
        return

    try:
        await member.kick(reason=f"بواسطة {interaction.user}: {reason}")
        log_ch = get_ch_log_ban(interaction.guild) or get_ch_admin_review(interaction.guild)
        if log_ch:
            embed = discord.Embed(title="👞 طرد عضو", color=discord.Color.red(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=f"{member} (`{member.id}`)", inline=False)
            embed.add_field(name="بواسطة", value=interaction.user.mention, inline=False)
            embed.add_field(name="السبب", value=reason, inline=False)
            try:
                await log_ch.send(embed=embed)
            except Exception:
                pass
        await interaction.response.send_message(f"✅ تم طرد **{member.name}**.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ فشل الطرد: {e}", ephemeral=True)


@bot.tree.command(name="تحذير", description="تحذير رسمي لعضو")
@discord.app_commands.describe(member="العضو", reason="السبب")
async def warn_cmd(interaction: discord.Interaction, member: discord.Member,
                   reason: str = "لم يُحدد"):
    if not await require_control(interaction):
        return
    allowed, wait = check_rate_limit(interaction.user.id, "تحذير")
    if not allowed:
        await interaction.response.send_message(f"⏱️ تجاوزت الحد. انتظر {wait} ثانية.", ephemeral=True)
        return

    if is_exempted(member):
        await interaction.response.send_message("❌ هذا العضو محمي!", ephemeral=True)
        return

    USER_WARNINGS.setdefault(member.id, []).append({
        "reason": reason,
        "warned_by": interaction.user.name,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    await save_warnings()
    warn_count = len(USER_WARNINGS[member.id])

    try:
        await member.send(
            f"⚠️ **تحذير من {interaction.guild.name}**\n"
            f"السبب: {reason}\nإجمالي: {warn_count}"
        )
    except Exception:
        pass

    jailed_msg = ""
    if warn_count >= 3:
        ok, msg = await apply_jail(interaction.guild, member,
                                   f"بلوغ {warn_count} تحذيرات")
        jailed_msg = f"\n{msg}"

    admin_ch = get_ch_admin_review(interaction.guild)
    if admin_ch:
        embed = discord.Embed(title="⚠️ تحذير جديد", color=discord.Color.gold(),
                              timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو", value=member.mention, inline=True)
        embed.add_field(name="بواسطة", value=interaction.user.mention, inline=True)
        embed.add_field(name="السبب", value=reason, inline=False)
        embed.add_field(name="الإجمالي", value=f"**{warn_count}**", inline=True)
        try:
            await admin_ch.send(embed=embed)
        except Exception:
            pass

    await interaction.response.send_message(
        f"✅ تحذير لـ {member.mention} (إجمالي: **{warn_count}**){jailed_msg}",
        ephemeral=True,
    )


@bot.tree.command(name="التحذيرات", description="عرض تحذيرات عضو")
@discord.app_commands.describe(member="العضو")
async def check_warnings_cmd(interaction: discord.Interaction, member: discord.Member):
    warnings = USER_WARNINGS.get(member.id, [])
    embed = discord.Embed(title=f"📋 تحذيرات {member.display_name}",
                          color=discord.Color.orange())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="الإجمالي", value=f"**{len(warnings)}**", inline=False)
    if warnings:
        details = "\n".join(
            f"**{i}.** `{w['reason']}` — بواسطة `{w['warned_by']}` ({w['date']})"
            for i, w in enumerate(warnings, 1)
        )
        embed.add_field(name="التفاصيل", value=details[:1024], inline=False)
    else:
        embed.description = "✅ لا يوجد تحذيرات."
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="حجر", description="حجر عضو")
@discord.app_commands.describe(member="العضو", reason="السبب")
async def jail_cmd(interaction: discord.Interaction, member: discord.Member,
                   reason: str = "لم يُحدد"):
    if not await require_control(interaction):
        return
    allowed, wait = check_rate_limit(interaction.user.id, "حجر")
    if not allowed:
        await interaction.response.send_message(f"⏱️ تجاوزت الحد. انتظر {wait} ثانية.", ephemeral=True)
        return

    ok, msg = await apply_jail(interaction.guild, member,
                               f"حجر يدوي بواسطة {interaction.user}: {reason}")
    if ok:
        admin_ch = get_ch_admin_review(interaction.guild)
        if admin_ch:
            embed = discord.Embed(title="🔒 حجر عضو", color=discord.Color.dark_red(),
                                  timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=member.mention, inline=False)
            embed.add_field(name="بواسطة", value=interaction.user.mention, inline=False)
            embed.add_field(name="السبب", value=reason, inline=False)
            try:
                await admin_ch.send(embed=embed)
            except Exception:
                pass
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="فك_الحجر", description="فك حجر عضو + تصفير تحذيراته")
@discord.app_commands.describe(member="العضو")
async def unjail_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction):
        return
    ok, msg = await remove_jail(interaction.guild, member)
    if member.id in USER_WARNINGS:
        del USER_WARNINGS[member.id]
        await save_warnings()
    await interaction.response.send_message(
        f"{msg}\n✅ تم تصفير التحذيرات أيضاً.", ephemeral=True
    )


@bot.tree.command(name="تصفير_مخالفات", description="تصفير تحذيرات عضو")
@discord.app_commands.describe(member="العضو")
async def reset_violations_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction):
        return
    if member.id in USER_WARNINGS:
        del USER_WARNINGS[member.id]
        await save_warnings()
        await interaction.response.send_message(
            f"✅ تم تصفير تحذيرات {member.mention}.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ لا توجد تحذيرات لـ {member.mention}.", ephemeral=True
        )


@bot.tree.command(name="تصفير_نيوك", description="تصفير سجل النيوكات لعضو")
@discord.app_commands.describe(member="العضو")
async def reset_nuke_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction):
        return
    gid = interaction.guild.id
    if member.id in NUKE_STRIKES[gid]:
        del NUKE_STRIKES[gid][member.id]
        await save_nuke_strikes()
        clear_user_tracker(gid, member.id)
        await interaction.response.send_message(
            f"✅ تم تصفير سجل النيوكات لـ {member.mention}.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ لا يوجد سجل نيوكات لـ {member.mention}.", ephemeral=True
        )


# ============================================================
# 🎯 الأوامر — الحماية
# ============================================================

@bot.tree.command(name="تعيين_نائب", description="[المالك] تعيين نائب")
@discord.app_commands.describe(member="العضو")
async def setdeputy_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_owner(interaction):
        return
    if member.id in deputy_user_ids:
        await interaction.response.send_message("⚠️ نائب مسبقاً.", ephemeral=True)
        return
    deputy_user_ids.append(member.id)
    await save_state()
    await interaction.response.send_message(
        f"✅ تم تعيين {member.mention} نائباً.", ephemeral=True
    )


@bot.tree.command(name="إزالة_نائب", description="[المالك] إزالة نائب")
@discord.app_commands.describe(member="العضو")
async def removedeputy_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_owner(interaction):
        return
    if member.id not in deputy_user_ids:
        await interaction.response.send_message("❌ ليس نائباً.", ephemeral=True)
        return
    deputy_user_ids.remove(member.id)
    await save_state()
    await interaction.response.send_message(
        f"✅ أُزيلت صفة النائب عن {member.mention}.", ephemeral=True
    )


@bot.tree.command(name="حماية_شخص", description="حماية شخص")
@discord.app_commands.describe(member="العضو")
async def protect_person_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction):
        return
    if member.id in protected_users_list:
        await interaction.response.send_message("⚠️ محمي مسبقاً.", ephemeral=True)
        return
    protected_users_list.append(member.id)
    await save_state()
    await interaction.response.send_message(f"🛡️ تم حماية {member.mention}.", ephemeral=True)


@bot.tree.command(name="إزالة_حماية_شخص", description="إزالة حماية شخص")
@discord.app_commands.describe(member="العضو")
async def unprotect_person_cmd(interaction: discord.Interaction, member: discord.Member):
    if not await require_control(interaction):
        return
    if member.id not in protected_users_list:
        await interaction.response.send_message("❌ ليس محمياً.", ephemeral=True)
        return
    protected_users_list.remove(member.id)
    await save_state()
    await interaction.response.send_message(f"🔓 أُزيلت حماية {member.mention}.", ephemeral=True)


@bot.tree.command(name="حماية_رتبه", description="حماية رتبة من الحذف/التعديل")
@discord.app_commands.describe(role="الرتبة")
async def protect_role_cmd(interaction: discord.Interaction, role: discord.Role):
    if not await require_control(interaction):
        return
    if role.id in protected_roles_list:
        await interaction.response.send_message("⚠️ محمية مسبقاً.", ephemeral=True)
        return
    protected_roles_list.append(role.id)
    await save_state()
    await interaction.response.send_message(f"🛡️ تم حماية {role.mention}.", ephemeral=True)


@bot.tree.command(name="إزالة_حماية_رتبه", description="إزالة حماية رتبة")
@discord.app_commands.describe(role="الرتبة")
async def unprotect_role_cmd(interaction: discord.Interaction, role: discord.Role):
    if not await require_control(interaction):
        return
    if role.id not in protected_roles_list:
        await interaction.response.send_message("❌ ليست محمية.", ephemeral=True)
        return
    protected_roles_list.remove(role.id)
    await save_state()
    await interaction.response.send_message(f"🔓 أُزيلت حماية {role.mention}.", ephemeral=True)


@bot.tree.command(name="حماية_روم", description="إضافة روم لقائمة الرومات المحمية")
@discord.app_commands.describe(channel="الروم")
async def protect_channel_cmd(interaction: discord.Interaction,
                              channel: discord.abc.GuildChannel):
    if not await require_control(interaction):
        return
    if channel.id in config.PROTECTED_CHANNELS:
        await interaction.response.send_message("⚠️ محمي مسبقاً.", ephemeral=True)
        return
    config.PROTECTED_CHANNELS.append(channel.id)
    await interaction.response.send_message(
        f"🛡️ تم حماية {channel.mention} (لحين إعادة التشغيل فقط — أضفه في config.py للدائم).",
        ephemeral=True,
    )


@bot.tree.command(name="قائمة_الحماية", description="عرض قوائم الحماية")
async def protection_dashboard_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ لوحة الحماية", color=discord.Color.gold())

    users_text = "\n".join(f"• <@{uid}>" for uid in protected_users_list
                           if interaction.guild.get_member(uid)) or "لا يوجد"
    roles_text = "\n".join(f"• <@&{rid}>" for rid in protected_roles_list
                           if interaction.guild.get_role(rid)) or "لا توجد"
    deputies_text = "\n".join(f"• <@{uid}>" for uid in deputy_user_ids
                              if interaction.guild.get_member(uid)) or "لا يوجد"
    bots_text = "\n".join(f"• <@{bid}>" for bid in trusted_bots) or "لا يوجد"

    embed.add_field(name=f"👤 محميون ({len(protected_users_list)})",
                    value=users_text[:1024], inline=False)
    embed.add_field(name=f"👑 رتب محمية ({len(protected_roles_list)})",
                    value=roles_text[:1024], inline=False)
    embed.add_field(name=f"🛡️ نواب ({len(deputy_user_ids)})",
                    value=deputies_text[:1024], inline=False)
    embed.add_field(name=f"🤖 بوتات موثوقة ({len(trusted_bots)})",
                    value=bots_text[:1024], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="بوت_موثوق", description="إضافة بوت لقائمة الموثوقين")
@discord.app_commands.describe(bot_member="البوت")
async def trust_bot_cmd(interaction: discord.Interaction, bot_member: discord.Member):
    if not await require_control(interaction):
        return
    if not bot_member.bot:
        await interaction.response.send_message("❌ هذا ليس بوت.", ephemeral=True)
        return
    if bot_member.id in trusted_bots:
        await interaction.response.send_message("⚠️ موثوق مسبقاً.", ephemeral=True)
        return
    trusted_bots.append(bot_member.id)
    await save_state()
    await interaction.response.send_message(
        f"✅ تم توثيق البوت {bot_member.mention}.", ephemeral=True
    )


@bot.tree.command(name="إزالة_بوت_موثوق", description="إزالة بوت من قائمة الموثوقين")
@discord.app_commands.describe(bot_member="البوت")
async def untrust_bot_cmd(interaction: discord.Interaction, bot_member: discord.Member):
    if not await require_control(interaction):
        return
    if bot_member.id not in trusted_bots:
        await interaction.response.send_message("❌ غير موجود في القائمة.", ephemeral=True)
        return
    trusted_bots.remove(bot_member.id)
    await save_state()
    await interaction.response.send_message(
        f"✅ أُزيل توثيق {bot_member.mention}.", ephemeral=True
    )


# ============================================================
# 🎯 الأوامر — Anti-Nuke
# ============================================================

@bot.tree.command(name="anti_nuke", description="تفعيل/تعطيل نظام Anti-Nuke")
@discord.app_commands.describe(state="on / off / status")
async def antinuke_cmd(interaction: discord.Interaction, state: str = "status"):
    if not await require_control(interaction):
        return

    state = state.lower()

    if state == "status":
        status = "✅ مفعّل" if config.ANTI_NUKE_ENABLED else "❌ معطّل"
        lines = [f"**الحالة:** {status}",
                 f"**العقوبة:** `{config.ANTI_NUKE_PUNISHMENT}`",
                 f"**تحذير متدرج:** {'نعم' if config.GRADUATED_NUKE_PUNISHMENT else 'لا'}",
                 ""]
        lines.append("**العتبات:**")
        for action, cfg in config.ANTI_NUKE_THRESHOLDS.items():
            lines.append(f"• `{action}`: {cfg['count']} / {cfg['seconds']}ث")
        embed = discord.Embed(title="🛡️ حالة Anti-Nuke",
                              description="\n".join(lines),
                              color=discord.Color.green() if config.ANTI_NUKE_ENABLED
                              else discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if state == "on":
        config.ANTI_NUKE_ENABLED = True
        await interaction.response.send_message("✅ تم تفعيل Anti-Nuke.", ephemeral=True)
    elif state == "off":
        config.ANTI_NUKE_ENABLED = False
        await interaction.response.send_message(
            "⚠️ تم تعطيل Anti-Nuke (لحين إعادة التشغيل).", ephemeral=True
        )
    else:
        await interaction.response.send_message("❌ استخدم: on / off / status", ephemeral=True)


# ============================================================
# 🎯 الأوامر — النسخ الاحتياطية
# ============================================================

@bot.tree.command(name="اعادة_لقطه", description="أخذ لقطة جديدة من السيرفر (cache)")
async def refresh_cache_cmd(interaction: discord.Interaction):
    if not await require_control(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    await cache_full_guild(interaction.guild)
    await backup_guild_name(interaction.guild)
    await backup_guild_icon(interaction.guild)
    await backup_guild_banner(interaction.guild)
    await interaction.followup.send(
        "✅ تم أخذ لقطة جديدة وحفظ النسخ الاحتياطية.", ephemeral=True
    )


@bot.tree.command(name="استرجاع_الاسم", description="استرجاع آخر اسم للسيرفر")
async def restore_name_cmd(interaction: discord.Interaction):
    if not await require_control(interaction):
        return
    ok, msg = await restore_guild_name(interaction.guild)
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="استرجاع_الايقونه", description="استرجاع آخر أيقونة للسيرفر")
async def restore_icon_cmd(interaction: discord.Interaction):
    if not await require_control(interaction):
        return
    ok, msg = await restore_guild_icon(interaction.guild)
    await interaction.response.send_message(msg, ephemeral=True)


@bot.tree.command(name="استرجاع_البانر", description="استرجاع آخر بانر للسيرفر")
async def restore_banner_cmd(interaction: discord.Interaction):
    if not await require_control(interaction):
        return
    ok, msg = await restore_guild_banner(interaction.guild)
    await interaction.response.send_message(msg, ephemeral=True)


# ============================================================
# 🎯 الأوامر — الرومات الصوتية
# ============================================================

@bot.tree.command(name="روم_صوتي", description="تحديد روم صوتي دائم للبوت")
@discord.app_commands.describe(voice_channel="الروم الصوتي")
async def voice_cmd(interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
    if not await require_control(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    global VOICE_CHANNEL_ID
    VOICE_CHANNEL_ID = voice_channel.id
    await save_state()
    try:
        if interaction.guild.me.voice:
            await interaction.guild.me.voice.disconnect()
        await voice_channel.connect()
        await interaction.followup.send(
            f"✅ تم الاتصال بـ **{voice_channel.name}**.", ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ فشل الاتصال: {e}", ephemeral=True)


# ============================================================
# 🎯 الأوامر — عامة
# ============================================================

@bot.tree.command(name="مسح", description="حذف رسائل")
@discord.app_commands.describe(amount="عدد الرسائل (1-100)")
async def clear_cmd(interaction: discord.Interaction, amount: int):
    if not await require_control(interaction):
        return
    allowed, wait = check_rate_limit(interaction.user.id, "مسح")
    if not allowed:
        await interaction.response.send_message(f"⏱️ تجاوزت الحد. انتظر {wait} ثانية.", ephemeral=True)
        return
    if not 1 <= amount <= 100:
        await interaction.response.send_message("❌ المدى 1-100 فقط.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ حُذفت {len(deleted)} رسالة.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ فشل الحذف: {e}", ephemeral=True)


@bot.tree.command(name="اعلان", description="نشر إعلان")
@discord.app_commands.describe(text="نص الإعلان")
async def announce_cmd(interaction: discord.Interaction, text: str):
    if not await require_control(interaction):
        return
    allowed, wait = check_rate_limit(interaction.user.id, "اعلان")
    if not allowed:
        await interaction.response.send_message(f"⏱️ تجاوزت الحد. انتظر {wait} ثانية.", ephemeral=True)
        return

    ch = get_ch_announce(interaction.guild)
    if not ch:
        await interaction.response.send_message("❌ لم أجد روم الإعلانات.", ephemeral=True)
        return
    embed = discord.Embed(title="📢 إعلان", description=text, color=discord.Color.gold())
    embed.set_footer(text=f"بواسطة {interaction.user.name}",
                     icon_url=interaction.user.display_avatar.url)
    msg = await ch.send(embed=embed)
    try:
        await msg.pin()
    except Exception:
        pass
    await interaction.response.send_message(f"✅ تم النشر في {ch.mention}.", ephemeral=True)


@bot.tree.command(name="قول", description="إرسال رسالة عبر البوت")
@discord.app_commands.describe(channel="الروم", message="الرسالة")
async def say_cmd(interaction: discord.Interaction,
                  channel: discord.TextChannel, message: str):
    if not await require_control(interaction):
        return
    try:
        await channel.send(message)
        await interaction.response.send_message(f"✅ أُرسلت إلى {channel.mention}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ فشل: {e}", ephemeral=True)


@bot.tree.command(name="خاص", description="إرسال DM عبر البوت")
@discord.app_commands.describe(member="العضو", message="الرسالة")
async def dm_cmd(interaction: discord.Interaction,
                 member: discord.Member, message: str):
    if not await require_control(interaction):
        return
    try:
        await member.send(f"📬 رسالة من **{interaction.guild.name}**:\n\n{message}")
        await interaction.response.send_message(f"✅ أُرسلت إلى {member.mention}.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ الخاصة مقفلة.", ephemeral=True)


@bot.tree.command(name="المالك", description="معلومات المالك")
async def owner_info_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="👑 مالك البوت", color=discord.Color.purple())
    embed.add_field(name="الاسم", value="Abo Shehri", inline=False)
    embed.add_field(name="التواصل", value="`ii.ih`", inline=False)
    await interaction.response.send_message(embed=embed)


# ============================================================
# 🎬 on_ready
# ============================================================

@bot.event
async def on_ready():
    log.info(f"✅ البوت متصل: {bot.user} (ID: {bot.user.id})")

    # تسجيل الواجهات الدائمة
    bot.add_view(TicketButtonView())
    bot.add_view(CloseTicketButton())
    bot.add_view(ApplicationButtonView())

    # تحميل cache السيرفرات
    load_guild_cache()
    for guild in bot.guilds:
        try:
            await cache_full_guild(guild)
            # حفظ نسخة من الاسم والأيقونة والبانر
            backup_guild_name(guild)
            await backup_guild_icon(guild)
            await backup_guild_banner(guild)
        except Exception as e:
            log.warning(f"فشل تهيئة {guild.name}: {e}")

    # مزامنة الأوامر
    try:
        synced = await bot.tree.sync()
        log.info(f"تمت مزامنة {len(synced)} أمر slash")
    except Exception as e:
        log.error(f"فشل مزامنة الأوامر: {e}")

    # الاتصال بالروم الصوتي
    if VOICE_CHANNEL_ID:
        for guild in bot.guilds:
            ch = guild.get_channel(VOICE_CHANNEL_ID)
            if isinstance(ch, discord.VoiceChannel):
                try:
                    await ch.connect()
                except Exception as e:
                    log.warning(f"فشل الاتصال الصوتي: {e}")


# ============================================================
# 🚀 نقطة البداية
# ============================================================

# ============================================================
# 🚀 تحميل الإضافات
# ============================================================

def load_extras_module():
    """يحمل extras.py ويمررتركة"""
    try:
        import extras

        shared = {
            # التحميل والحفظ
            "save_warnings": save_warnings,
            "save_state": save_state,

            # الصلاحيات
            "require_control": require_control,
            "require_owner": require_owner,
            "is_exempted": is_exempted,
            "can_act_on": can_act_on,

            # Rate Limiting
            "check_rate_limit": check_rate_limit,

            # الحجر
            "apply_jail": apply_jail,
            "remove_jail": remove_jail,

            # الرومات
            "get_ch_admin_review": get_ch_admin_review,
            "get_ch_jail": get_ch_jail,
            "get_ch_welcome": get_ch_welcome,
            "get_ch_announce": get_ch_announce,

            # الكاش والنسخ الاحتياطية
            "cache_full_guild": cache_full_guild,
            "backup_guild_name": backup_guild_name,
            "backup_guild_icon": backup_guild_icon,
            "backup_guild_banner": backup_guild_banner,

            # الحالة المشتركة
            "USER_WARNINGS": USER_WARNINGS,
        }

        extras.load_extras(bot, shared)
        log.info("✅ تم تحميل extras.py بنجاح")
    except ImportError as e:
        log.warning(f"⚠️ extras.py غير موجود — تم تجاهل الإضافات: {e}")
    except Exception as e:
        log.exception(f"❌ خطأ في تحميل extras.py: {e}")


def main():
    load_all_state()
    keep_alive()

    # ✅ تحميل الإضافات
    load_extras_module()

    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("❌ متغير DISCORD_TOKEN غير موجود!")
    bot.run(token, log_handler=None)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
