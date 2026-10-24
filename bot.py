import os
import re
import json
import time
import asyncio
import logging
import datetime
from collections import defaultdict, deque
from typing import Optional

import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

import config

# ═══════════════════════════════════════════════════════════════
# ⚙️ الإعدادات الأساسية
# ═══════════════════════════════════════════════════════════════

# ضع التوكن الخاص بك هنا مباشرة إذا لم يعمل من المتغيرات
# أو اتركه فارغاً وضعه في Environment Variables في Wispbyte
TOKEN = "MTUxOTQ3Mjk0NTIyMTczMDUyNA.GnB-gR.5YE42EUdyXyNYBm6kDFpVe_BkWa88fs1E1O_f4"

os.makedirs(config.LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(config.BOT_LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("bot")

for d in [config.DATA_DIR, config.BACKUPS_DIR, config.ICONS_DIR, config.BANNERS_DIR, config.LOGS_DIR, config.CARDS_DIR]:
    os.makedirs(d, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!nobotprefix!", intents=intents, help_command=None)

# ═══════════════════════════════════════════════════════════════
# 💾 الحالة العامة
# ═══════════════════════════════════════════════════════════════
VOICE_CHANNEL_ID: int = 0
USER_WARNINGS: dict = {}
saved_roles: dict = {}
protected_users_list: list = []
protected_roles_list: list = []
deputy_user_ids: list = []
trusted_bots: list = []
NUKE_TRACKER: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
NUKE_STRIKES: dict = defaultdict(lambda: defaultdict(int))
RATE_LIMIT_TRACKER: dict = defaultdict(lambda: defaultdict(deque))
GUILD_CACHE: dict = defaultdict(lambda: {"channels": {}, "roles": {}})

def _read_json(path: str, default):
    if not os.path.exists(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def _write_json(path: str, data) -> None:
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e: log.error("خطأ في حفظ %s: %s", path, e)

async def async_save_json(path: str, data) -> None:
    await asyncio.to_thread(_write_json, path, data)

async def save_warnings() -> None:
    await async_save_json(config.WARNINGS_FILE, {str(k): v for k, v in USER_WARNINGS.items()})

async def save_state() -> None:
    data = {
        "protected_users": protected_users_list, "protected_roles": protected_roles_list,
        "deputies": deputy_user_ids, "trusted_bots": trusted_bots,
        "voice_channel_id": VOICE_CHANNEL_ID, "saved_roles": {str(k): v for k, v in saved_roles.items()},
    }
    await async_save_json(config.STATE_FILE, data)

async def save_nuke_strikes() -> None:
    data = {str(gid): {str(uid): c for uid, c in users.items()} for gid, users in NUKE_STRIKES.items()}
    await async_save_json(config.ANTINUKE_FILE, data)

async def load_all_state_async() -> None:
    global USER_WARNINGS, saved_roles, protected_users_list, protected_roles_list, deputy_user_ids, VOICE_CHANNEL_ID, trusted_bots, NUKE_STRIKES
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
        for uid, count in users.items(): NUKE_STRIKES[int(gid)][int(uid)] = count

# ═══════════════════════════════════════════════════════════════
# 🔍 البحث الذكي والصلاحيات
# ═══════════════════════════════════════════════════════════════
def find_role(guild: discord.Guild, cfg: dict) -> Optional[discord.Role]:
    if cfg.get("id"):
        role = guild.get_role(cfg["id"])
        if role: return role
    for name in cfg["names"]:
        role = discord.utils.get(guild.roles, name=name)
        if role: return role
    return None

def find_channel(guild: discord.Guild, cfg: dict, channel_type: str = "text") -> Optional[discord.abc.GuildChannel]:
    if cfg.get("id"):
        ch = guild.get_channel(cfg["id"])
        if ch: return ch
    if channel_type == "text": channels = guild.text_channels
    elif channel_type == "category": channels = guild.categories
    else: channels = guild.channels
    for name in cfg["names"]:
        for ch in channels:
            if ch.name == name or ch.name.startswith(name): return ch
    return None

def get_role_jail(g): return find_role(g, config.ROLE_JAIL)
def get_role_ticket(g): return find_role(g, config.ROLE_TICKET)
def get_role_apply(g): return find_role(g, config.ROLE_APPLY)
def get_role_citizen(g): return find_role(g, config.CITIZEN_ROLE)
def get_role_minister(g): return find_role(g, config.ROLE_MINISTER)

def get_ch_admin_review(g): return find_channel(g, config.CH_ADMIN_REVIEW, "text")
def get_ch_jail(g): return find_channel(g, config.CH_JAIL, "text")
def get_ch_log_manual(g): return find_channel(g, config.CH_LOG_MANUAL, "text")
def get_ch_log_auto(g): return find_channel(g, config.CH_LOG_AUTO, "text")
def get_ch_log_changes(g): return find_channel(g, config.CH_LOG_CHANGES, "text")
def get_ch_log_tickets(g): return find_channel(g, config.CH_LOG_TICKETS, "text")
def get_ch_log_leave(g): return find_channel(g, config.CH_LOG_LEAVE, "text")
def get_ch_log_nuke(g): return find_channel(g, config.CH_LOG_NUKE, "text")
def get_ch_log_guild(g): return find_channel(g, config.CH_LOG_GUILD, "text")
def get_ch_welcome(g): return find_channel(g, config.CH_WELCOME, "text")
def get_ch_announce(g): return find_channel(g, config.CH_ANNOUNCE, "text")
def get_ch_ticket_panel(g): return find_channel(g, config.CH_TICKET_PANEL, "text")
def get_ch_apply_panel(g): return find_channel(g, config.CH_APPLY_PANEL, "text")
def get_cat_ticket(g): return find_channel(g, config.CH_TICKET_CATEGORY, "category")

def is_owner(user_id: int) -> bool: return user_id == config.BOT_OWNER_ID
def is_deputy(user_id: int) -> bool: return user_id in deputy_user_ids
def has_control(user_id: int) -> bool: return is_owner(user_id) or is_deputy(user_id)

def is_exempted(member) -> bool:
    if member is None: return False
    user_id = member.id
    if is_owner(user_id) or is_deputy(user_id): return True
    if isinstance(member, discord.Member):
        if member.guild and user_id == member.guild.owner_id: return True
        protected_ids = set(protected_roles_list)
        if any(r.id in protected_ids for r in member.roles): return True
    if user_id in protected_users_list: return True
    if getattr(member, "bot", False) and user_id in trusted_bots: return True
    return False

async def require_control(interaction: discord.Interaction) -> bool:
    if has_control(interaction.user.id) or (interaction.guild and interaction.user.id == interaction.guild.owner_id): return True
    await interaction.response.send_message("🔒 **عذراً** — هذا الأمر مخصص لـ **مالك البوت والنواب** فقط.\n🇸🇦〢Kingdom of Saudi Arabia", ephemeral=True)
    return False

async def require_owner(interaction: discord.Interaction) -> bool:
    if is_owner(interaction.user.id) or (interaction.guild and interaction.user.id == interaction.guild.owner_id): return True
    await interaction.response.send_message("🔒 **عذراً** — هذا الأمر مخصص لـ **مالك البوت** فقط.\n🇸🇦〢Kingdom of Saudi Arabia", ephemeral=True)
    return False

def bot_can_manage(target, guild: discord.Guild):
    me = guild.me
    if isinstance(target, discord.Member):
        if target.id == guild.owner_id: return False, "لا أستطيع تعديل مالك السيرفر"
        if target.top_role >= me.top_role: return False, "رتبته أعلى أو تساوي رتبة البوت"
    if isinstance(target, discord.Role):
        if target.is_default(): return False, "لا يمكن تعديل @everyone"
        if target >= me.top_role: return False, "الرتبة أعلى أو تساوي رتبة البوت"
    return True, ""

def check_rate_limit(user_id: int, command: str):
    if command not in config.RATE_LIMITS: return True, 0
    limit = config.RATE_LIMITS[command]
    now = time.time()
    dq = RATE_LIMIT_TRACKER[user_id][command]
    while dq and now - dq[0] > limit["window"]: dq.popleft()
    if len(dq) >= limit["max"]: return False, int(limit["window"] - (now - dq[0])) + 1
    dq.append(now)
    return True, 0

# ═══════════════════════════════════════════════════════════════
# 🧹 تطبيع النص والكلمات المحظورة
# ═══════════════════════════════════════════════════════════════
_TASHKEEL_RE = re.compile(r'[\u0617-\u061A\u064B-\u0652]')
_NON_ALNUM_RE = re.compile(r'[^a-zA-Z\u0600-\u06FF]')
_DUP_RE = re.compile(r'(.)\1+')

def normalize_text(text: str):
    text = text.lower()
    text = _TASHKEEL_RE.sub('', text)
    cleaned = _NON_ALNUM_RE.sub('', text)
    return text, cleaned, _DUP_RE.sub(r'\1', cleaned)

BAD_WORDS_RE = re.compile("|".join([r'(?<![\u0600-\u06FF])' + re.escape(w) + r'(?![\u0600-\u06FF])' if re.search(r'[\u0600-\u06FF]', w) else r'(?<![a-zA-Z])' + re.escape(w) + r'(?![a-zA-Z])' for w in config.BAD_WORDS]), re.IGNORECASE)
URL_REGEX = re.compile(r"(https?://\S+|discord\.gg/\S+|discord\.com/invite/\S+|www\.\S+)", re.IGNORECASE)

# ═══════════════════════════════════════════════════════════════
# 🔒 نظام التوقيف
# ═══════════════════════════════════════════════════════════════
async def apply_jail(guild: discord.Guild, member: discord.Member, reason: str, duration_text: str = "دائم", issued_by=None):
    if is_exempted(member): return False, "🛡️ هذا العضو محمي، لا يمكن توقيفه."
    jail_role = get_role_jail(guild)
    if not jail_role: return False, "❌ لم أجد رتبة التوقيف في config.py."
    if jail_role >= guild.me.top_role: return False, "❌ رتبة التوقيف أعلى من رتبة البوت."
    try:
        if jail_role not in member.roles:
            saved_roles[member.id] = [r.id for r in member.roles if r != guild.default_role and r != jail_role]
        await member.edit(roles=[jail_role], reason=reason)
        if member.voice: await member.move_to(None)
        await save_state()
        return True, "🚔 تم تطبيق قرار التوقيف بنجاح."
    except Exception as e: return False, "❌ فشل التوقيف: " + str(e)

async def remove_jail(guild: discord.Guild, member: discord.Member):
    jail_role = get_role_jail(guild)
    if jail_role and jail_role in member.roles:
        try: await member.remove_roles(jail_role)
        except Exception: pass
    if member.id in saved_roles:
        roles_to_restore = [guild.get_role(rid) for rid in saved_roles.pop(member.id) if guild.get_role(rid) and guild.get_role(rid) < guild.me.top_role]
        if roles_to_restore:
            try: await member.add_roles(*roles_to_restore, reason="فك التوقيف")
            except Exception: pass
    await save_state()
    return True, "🔓 تم الإفراج عن العضو واستعادة الرتب."

# ═══════════════════════════════════════════════════════════════
# 🛡️ Anti-Nuke
# ═══════════════════════════════════════════════════════════════
def record_action(guild_id: int, user_id: int, action: str) -> int:
    if action not in config.ANTI_NUKE_THRESHOLDS: return 0
    dq = NUKE_TRACKER[guild_id][user_id][action]
    dq.append(time.time())
    while dq and time.time() - dq[0] > config.ANTI_NUKE_THRESHOLDS[action]["seconds"]: dq.popleft()
    return len(dq)

def is_nuke(guild_id: int, user_id: int, action: str) -> bool:
    return action in config.ANTI_NUKE_THRESHOLDS and record_action(guild_id, user_id, action) > config.ANTI_NUKE_THRESHOLDS[action]["count"]

async def get_audit_executor(guild: discord.Guild, action: discord.AuditLogAction, target_id: int):
    try:
        async for entry in guild.audit_logs(limit=5, action=action):
            if entry.target and entry.target.id == target_id and (discord.utils.utcnow() - entry.created_at).total_seconds() < 15:
                return entry.user
    except Exception: pass
    return None

async def handle_nuke_event(guild: discord.Guild, member: Optional[discord.Member], action: str, target_desc: str, restore_func=None):
    if not config.ANTI_NUKE_ENABLED or member is None or member.bot or is_exempted(member): return
    if not is_nuke(guild.id, member.id, action): return
    if restore_func:
        try: await restore_func()
        except Exception: pass
    NUKE_STRIKES[guild.id][member.id] += 1
    await save_nuke_strikes()
    ok, msg = await apply_jail(guild, member, f"Anti-Nuke: {action} (المرة {NUKE_STRIKES[guild.id][member.id]})")
    log_ch = get_ch_log_nuke(guild)
    if log_ch:
        embed = discord.Embed(title="🚨 محاولة تخريب", description=f"**تم كشف نشاط تخريبي وصدّه**\n\n👤 المخرب: {member.mention}\n⚔️ العملية: {action}\n🎯 الهدف: {target_desc}\n🔨 العقوبة: {msg}", color=discord.Color.red())
        try: await log_ch.send(embed=embed)
        except Exception: pass# ═══════════════════════════════════════════════════════════════
# 🗂️ Cache للرومات والرتب (النسخ الاحتياطي)
# ═══════════════════════════════════════════════════════════════
def snapshot_channel(channel: discord.abc.GuildChannel) -> dict:
    base = {"name": channel.name, "position": channel.position, "category_id": channel.category_id, "overwrites": {}}
    for target, ow in channel.overwrites.items():
        allow, deny = ow.pair()
        base["overwrites"][str(target.id)] = {"type": "role" if isinstance(target, discord.Role) else "member", "allow": allow.value, "deny": deny.value}
    if isinstance(channel, discord.TextChannel): base.update({"kind": "text", "topic": channel.topic, "nsfw": channel.nsfw, "slowmode": channel.slowmode_delay})
    elif isinstance(channel, discord.VoiceChannel): base.update({"kind": "voice", "bitrate": channel.bitrate, "user_limit": channel.user_limit})
    elif isinstance(channel, discord.CategoryChannel): base["kind"] = "category"
    else: base["kind"] = "unknown"
    return base

def snapshot_role(role: discord.Role) -> dict:
    return {"name": role.name, "color": role.color.value, "permissions": role.permissions.value, "position": role.position, "hoist": role.hoist, "mentionable": role.mentionable, "unicode_emoji": role.unicode_emoji}

def rebuild_overwrites(guild: discord.Guild, overwrites_data: dict) -> dict:
    result = {}
    for tid_str, ow in overwrites_data.items():
        target = guild.get_role(int(tid_str)) if ow["type"] == "role" else guild.get_member(int(tid_str))
        if target: result[target] = discord.PermissionOverwrite.from_pair(discord.Permissions(ow["allow"]), discord.Permissions(ow["deny"]))
    return result

async def cache_full_guild(guild: discord.Guild):
    channels_data = {ch.id: snapshot_channel(ch) for ch in guild.channels}
    roles_data = {r.id: snapshot_role(r) for r in guild.roles if not r.is_default() and not r.managed}
    GUILD_CACHE[guild.id] = {"channels": channels_data, "roles": roles_data}
    await async_save_json(config.GUILD_CACHE_FILE, {str(gid): {"channels": {str(k): v for k, v in d["channels"].items()}, "roles": {str(k): v for k, v in d["roles"].items()}} for gid, d in GUILD_CACHE.items()})

async def restore_channel_from_cache(guild: discord.Guild, ch_id: int):
    cache = GUILD_CACHE.get(guild.id)
    if not cache or ch_id not in cache["channels"]: return
    data = cache["channels"][ch_id]
    category = guild.get_channel(data.get("category_id")) if data.get("category_id") else None
    if category and not isinstance(category, discord.CategoryChannel): category = None
    try:
        ow = rebuild_overwrites(guild, data.get("overwrites", {}))
        kind = data.get("kind")
        if kind == "text": await guild.create_text_channel(name=data["name"], category=category, topic=data.get("topic"), slowmode_delay=data.get("slowmode", 0), overwrites=ow, reason="Anti-Nuke: استرجاع")
        elif kind == "voice": await guild.create_voice_channel(name=data["name"], category=category, bitrate=data.get("bitrate", 64000), overwrites=ow, reason="Anti-Nuke: استرجاع")
        elif kind == "category": await guild.create_category(name=data["name"], overwrites=ow, reason="Anti-Nuke: استرجاع")
    except Exception as e: log.warning("فشل استرجاع الروم: %s", e)

async def restore_role_from_cache(guild: discord.Guild, role_id: int):
    cache = GUILD_CACHE.get(guild.id)
    if not cache or role_id not in cache["roles"]: return
    data = cache["roles"][role_id]
    try:
        await guild.create_role(name=data["name"], color=discord.Color(data["color"]), permissions=discord.Permissions(data["permissions"]), hoist=data["hoist"], mentionable=data["mentionable"], reason="Anti-Nuke: استرجاع")
    except Exception as e: log.warning("فشل استرجاع الرتبة: %s", e)

# ═══════════════════════════════════════════════════════════════
# 🚨 أحداث Anti-Nuke
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    await asyncio.sleep(1)
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    await restore_channel_from_cache(channel.guild, channel.id)
    if executor: await handle_nuke_event(channel.guild, executor, "channel_delete", channel.name)

@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel):
    await asyncio.sleep(1)
    executor = await get_audit_executor(channel.guild, discord.AuditLogAction.channel_create, channel.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if executor:
        async def delete_new():
            try: await channel.delete(reason="Anti-Nuke")
            except Exception: pass
        await handle_nuke_event(channel.guild, executor, "channel_create", channel.name, restore_func=delete_new)

@bot.event
async def on_guild_role_delete(role: discord.Role):
    if role.is_default() or role.managed: return
    await asyncio.sleep(1)
    executor = await get_audit_executor(role.guild, discord.AuditLogAction.role_delete, role.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    await restore_role_from_cache(role.guild, role.id)
    if executor: await handle_nuke_event(role.guild, executor, "role_delete", role.name)

@bot.event
async def on_guild_role_create(role: discord.Role):
    if role.managed: return
    await asyncio.sleep(1)
    executor = await get_audit_executor(role.guild, discord.AuditLogAction.role_create, role.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if executor:
        async def delete_new():
            try: await role.delete(reason="Anti-Nuke")
            except Exception: pass
        await handle_nuke_event(role.guild, executor, "role_create", role.name, restore_func=delete_new)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    await asyncio.sleep(1)
    executor = await get_audit_executor(guild, discord.AuditLogAction.ban, user.id)
    if executor and (executor.id == bot.user.id or is_exempted(executor)): return
    if not executor: return
    is_protected = (user.id == config.BOT_OWNER_ID or user.id in deputy_user_ids or user.id in protected_users_list or user.id == guild.owner_id)
    if is_protected:
        try: await guild.unban(user, reason="Anti-Nuke")
        except Exception: pass
        await apply_jail(guild, executor, "حظر عضو محمي")
    else:
        async def unban():
            try: await guild.unban(user, reason="Anti-Nuke")
            except Exception: pass
        await handle_nuke_event(guild, executor, "ban", str(user), restore_func=unban)

# ═══════════════════════════════════════════════════════════════
# 👋 أحداث الأعضاء (ترحيب، حماية، مغادرة)
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_member_join(member: discord.Member):
    try: await member.send(f"🇸🇦 **أهلاً بك في {member.guild.name}**\n\n{config.RULES_TEXT}")
    except Exception: pass
    ch = get_ch_welcome(member.guild)
    if ch:
        embed = discord.Embed(title="🇸🇦 عضو جديد!", description=f"أهلاً {member.mention}\nنتمنى لك وقتاً ممتعاً.\n\nعدد الأعضاء: **{member.guild.member_count}**", color=discord.Color.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        try: await ch.send(content=member.mention, embed=embed)
        except Exception: pass

@bot.event
async def on_member_remove(member: discord.Member):
    await asyncio.sleep(1)
    executor = await get_audit_executor(member.guild, discord.AuditLogAction.kick, member.id)
    if executor and not is_exempted(executor) and executor.id != bot.user.id:
        await handle_nuke_event(member.guild, executor, "kick", str(member))
        return
    ch = get_ch_log_leave(member.guild)
    if ch:
        try: await ch.send(embed=discord.Embed(title="📤 عضو غادر", description=f"**{member}** غادر السيرفر\nالأعضاء الآن: {member.guild.member_count}", color=discord.Color.red()))
        except Exception: pass

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.roles != after.roles:
        if is_exempted(after) and after.id != bot.user.id:
            removed = [r for r in before.roles if r not in after.roles and r != after.guild.default_role and r != get_role_jail(after.guild)]
            if removed:
                await asyncio.sleep(1)
                executor = await get_audit_executor(after.guild, discord.AuditLogAction.member_role_update, after.id)
                if executor and not is_exempted(executor) and executor.id != bot.user.id:
                    try: await after.add_roles(*removed)
                    except Exception: pass
                    await apply_jail(after.guild, executor, f"محاولة سحب رتب من محمي: {after}")
        
        added = [r for r in after.roles if r not in before.roles]
        if added and after.id != bot.user.id:
            if getattr(config, "ROLE_NOTIFY_ENABLED", True):
                try: await after.send("🎖️ **رتب جديدة:**\n" + "\n".join([f"• {r.mention}" for r in added]))
                except Exception: pass

# ═══════════════════════════════════════════════════════════════
# 💬 فلترة الرسائل
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild: return
    if is_exempted(message.author):
        await bot.process_commands(message)
        return
    
    violation = None
    raw = message.content or ""
    if message.mention_everyone: violation = "منشن الجميع"
    else:
        _, cleaned, collapsed = normalize_text(raw)
        if BAD_WORDS_RE.search(cleaned) or BAD_WORDS_RE.search(collapsed): violation = "ألفاظ نابية"
        elif URL_REGEX.search(raw): violation = "روابط"
        
    if violation:
        try: await message.delete()
        except Exception: pass
        USER_WARNINGS.setdefault(message.author.id, []).append({"reason": violation, "date": datetime.datetime.now().strftime("%Y-%m-%d")})
        await save_warnings()
        warns = len(USER_WARNINGS[message.author.id])
        if violation == "ألفاظ نابية" or warns >= 3:
            await apply_jail(message.guild, message.author, f"مخالفة: {violation}")
        else:
            try: await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(hours=1), reason=violation)
            except Exception: pass
        
        log_ch = get_ch_log_auto(message.guild)
        if log_ch:
            try: await log_ch.send(embed=discord.Embed(title="🚨 مخالفة", description=f"العضو: {message.author.mention}\nالمخالفة: {violation}\nالإنذارات: {warns}/3", color=discord.Color.red()))
            except Exception: pass
    else:
        await bot.process_commands(message)# ═══════════════════════════════════════════════════════════════
# 📜 نظام البرقيات (Tickets)
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
# 🇸🇦 نظام الجنسية
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
# 🎬 التشغيل
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    log.info("البوت متصل: %s (ID: %s)", bot.user, bot.user.id)
    bot.add_view(TicketButtonView())
    bot.add_view(CloseTicketButton())
    bot.add_view(ApplicationButtonView())
    await load_all_state_async()
    for guild in bot.guilds:
        await cache_full_guild(guild)
    try:
        await bot.tree.sync()
        log.info("تمت مزامنة الأوامر بنجاح")
    except Exception as e: log.error("فشل مزامنة الأوامر: %s", e)

def main():
    if not TOKEN or TOKEN == "ضع_التوكن_هنا_إذا_لم_يعمل_المتغير":
        log.error("❌ التوكن غير موجود! ضعه في الكود أو في المتغيرات.")
        return
    bot.run(TOKEN)

if __name__ == "__main__":
    main()
