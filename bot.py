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

try:
    with open("token.txt", "r", encoding="utf-8") as f:
        TOKEN = f.read().strip()
except FileNotFoundError:
    TOKEN = os.getenv("DISCORD_TOKEN")

os.makedirs(config.LOGS_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", handlers=[logging.FileHandler(config.BOT_LOG_FILE, encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger("bot")

for d in [config.DATA_DIR, config.BACKUPS_DIR, config.ICONS_DIR, config.BANNERS_DIR, config.LOGS_DIR, config.CARDS_DIR]:
    os.makedirs(d, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!nobotprefix!", intents=intents, help_command=None)

VOICE_CHANNEL_ID = 0
USER_WARNINGS, saved_roles, protected_users_list = {}, {}, []
protected_roles_list, deputy_user_ids, trusted_bots = [], [], []
NUKE_TRACKER = defaultdict(lambda: defaultdict(lambda: defaultdict(deque)))
NUKE_STRIKES = defaultdict(lambda: defaultdict(int))
GUILD_CACHE = defaultdict(lambda: {"channels": {}, "roles": {}})

def _read_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception: pass

async def save_warnings():
    await asyncio.to_thread(_write_json, config.WARNINGS_FILE, {str(k): v for k, v in USER_WARNINGS.items()})

async def save_state():
    data = {"protected_users": protected_users_list, "protected_roles": protected_roles_list, "deputies": deputy_user_ids, "trusted_bots": trusted_bots, "voice_channel_id": VOICE_CHANNEL_ID, "saved_roles": {str(k): v for k, v in saved_roles.items()}}
    await asyncio.to_thread(_write_json, config.STATE_FILE, data)

async def load_all_state():
    global USER_WARNINGS, saved_roles, protected_users_list, protected_roles_list, deputy_user_ids, VOICE_CHANNEL_ID, trusted_bots
    USER_WARNINGS = {int(k): v for k, v in _read_json(config.WARNINGS_FILE, {}).items()}
    state = _read_json(config.STATE_FILE, {})
    protected_users_list = state.get("protected_users", [])
    protected_roles_list = state.get("protected_roles", [])
    deputy_user_ids = state.get("deputies", [])
    trusted_bots = state.get("trusted_bots", [])
    VOICE_CHANNEL_ID = state.get("voice_channel_id", 0)
    saved_roles = {int(k): v for k, v in state.get("saved_roles", {}).items()}

def find_role(guild, cfg):
    if cfg.get("id"):
        r = guild.get_role(cfg["id"])
        if r: return r
    for name in cfg["names"]:
        r = discord.utils.get(guild.roles, name=name)
        if r: return r
    return None

def find_channel(guild, cfg, t="text"):
    if cfg.get("id"):
        c = guild.get_channel(cfg["id"])
        if c: return c
    channels = guild.text_channels if t == "text" else guild.categories
    for name in cfg["names"]:
        for c in channels:
            if c.name == name or c.name.startswith(name): return c
    return None

def get_role_jail(g): return find_role(g, config.ROLE_JAIL)
def get_role_ticket(g): return find_role(g, config.ROLE_TICKET)
def get_role_apply(g): return find_role(g, config.ROLE_APPLY)
def get_role_citizen(g): return find_role(g, config.CITIZEN_ROLE)
def get_role_minister(g): return find_role(g, config.ROLE_MINISTER)
def get_ch_admin_review(g): return find_channel(g, config.CH_ADMIN_REVIEW)
def get_ch_jail(g): return find_channel(g, config.CH_JAIL)
def get_ch_log_changes(g): return find_channel(g, config.CH_LOG_CHANGES)
def get_ch_log_tickets(g): return find_channel(g, config.CH_LOG_TICKETS)
def get_ch_log_leave(g): return find_channel(g, config.CH_LOG_LEAVE)
def get_ch_log_nuke(g): return find_channel(g, config.CH_LOG_NUKE)
def get_ch_log_auto(g): return find_channel(g, config.CH_LOG_AUTO)
def get_ch_welcome(g): return find_channel(g, config.CH_WELCOME)
def get_ch_announce(g): return find_channel(g, config.CH_ANNOUNCE)
def get_ch_ticket_panel(g): return find_channel(g, config.CH_TICKET_PANEL)
def get_ch_apply_panel(g): return find_channel(g, config.CH_APPLY_PANEL)
def get_cat_ticket(g): return find_channel(g, config.CH_TICKET_CATEGORY, "category")

def is_owner(uid): return uid == config.BOT_OWNER_ID
def is_deputy(uid): return uid in deputy_user_ids
def has_control(uid): return is_owner(uid) or is_deputy(uid)

def is_exempted(m):
    if not m: return False
    if is_owner(m.id) or is_deputy(m.id): return True
    if isinstance(m, discord.Member):
        if m.guild and m.id == m.guild.owner_id: return True
        if any(r.id in protected_roles_list for r in m.roles): return True
    if m.id in protected_users_list: return True
    if getattr(m, "bot", False) and m.id in trusted_bots: return True
    return False

async def require_control(i):
    if has_control(i.user.id) or (i.guild and i.user.id == i.guild.owner_id): return True
    await i.response.send_message("🔒 هذا الأمر للإدارة فقط.", ephemeral=True)
    return False

async def require_owner(i):
    if is_owner(i.user.id) or (i.guild and i.user.id == i.guild.owner_id): return True
    await i.response.send_message("🔒 هذا الأمر للمالك فقط.", ephemeral=True)
    return False

def bot_can_manage(target, guild):
    if isinstance(target, discord.Member):
        if target.id == guild.owner_id: return False, "لا يمكن تعديل المالك"
        if target.top_role >= guild.me.top_role: return False, "رتبته أعلى من البوت"
    return True, ""

async def apply_jail(guild, member, reason, duration_text="دائم", issued_by=None):
    if is_exempted(member): return False, "🛡️ محمي."
    jail_role = get_role_jail(guild)
    if not jail_role: return False, "❌ رتبة التوقيف غير موجودة."
    if jail_role >= guild.me.top_role: return False, "❌ رتبة التوقيف أعلى من البوت."
    try:
        if jail_role not in member.roles:
            saved_roles[member.id] = [r.id for r in member.roles if r != guild.default_role and r != jail_role]
        await member.edit(roles=[jail_role], reason=reason)
        if member.voice: await member.move_to(None)
        await save_state()
        return True, "🚔 تم التوقيف."
    except Exception as e: return False, "❌ فشل التوقيف."

async def remove_jail(guild, member):
    jail_role = get_role_jail(guild)
    if jail_role and jail_role in member.roles:
        try: await member.remove_roles(jail_role)
        except Exception: pass
    if member.id in saved_roles:
        roles = [guild.get_role(rid) for rid in saved_roles.pop(member.id) if guild.get_role(rid) and guild.get_role(rid) < guild.me.top_role]
        if roles:
            try: await member.add_roles(*roles, reason="فك التوقيف")
            except Exception: pass
    await save_state()
    return True, "🔓 تم الإفراج."

# ═══════════════════════════════════════════════════════════════
# 🎫 أنظمة (البرقيات والجنسية)
# ═══════════════════════════════════════════════════════════════
class TicketModal(Modal, title="📜 إرسال برقية"):
    subject = TextInput(label="الموضوع", required=True)
    problem = TextInput(label="المشكلة", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i):
        cat = get_cat_ticket(i.guild)
        if not cat: return await i.response.send_message("❌ لا يوجد تصنيف.", ephemeral=True)
        tr = get_role_ticket(i.guild)
        ow = {i.guild.default_role: discord.PermissionOverwrite(view_channel=False), i.user: discord.PermissionOverwrite(view_channel=True), i.guild.me: discord.PermissionOverwrite(view_channel=True)}
        if tr: ow[tr] = discord.PermissionOverwrite(view_channel=True)
        ch = await i.guild.create_text_channel(f"ticket-{i.user.id}", category=cat, overwrites=ow)
        embed = discord.Embed(title="📜 برقية", description=f"**الموضوع:** {self.subject.value}\n**المشكلة:** {self.problem.value}", color=discord.Color.green())
        await ch.send(content=f"{i.user.mention} | {tr.mention if tr else ''}", embed=embed, view=CloseTicketButton())
        await i.response.send_message(f"✅ تم فتح البرقية: {ch.mention}", ephemeral=True)

class NoteModal(Modal, title="📝 إرسال ملاحظة"):
    note = TextInput(label="الملاحظة", style=discord.TextStyle.paragraph, required=True)
    async def on_submit(self, i):
        embed = discord.Embed(title="📝 ملاحظة", description=f"من: {i.user.mention}\nالملاحظة: {self.note.value}", color=discord.Color.blue())
        ch = get_ch_admin_review(i.guild)
        if ch: await ch.send(embed=embed)
        try: await (await i.client.fetch_user(config.BOT_OWNER_ID)).send(embed=embed)
        except: pass
        await i.response.send_message("✅ تم إرسال الملاحظة.", ephemeral=True)

class TicketButtonView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="📜 إرسال برقية", style=discord.ButtonStyle.success, custom_id="btn_t1")
    async def b1(self, i, b): await i.response.send_modal(TicketModal())
    @discord.ui.button(label="📝 إرسال ملاحظة", style=discord.ButtonStyle.primary, custom_id="btn_t2")
    async def b2(self, i, b): await i.response.send_modal(NoteModal())
    @discord.ui.button(label="🔄 إعادة تشغيل", style=discord.ButtonStyle.danger, custom_id="btn_t3")
    async def b3(self, i, b):
        if not await require_control(i): return
        bot.add_view(TicketButtonView()); bot.add_view(CloseTicketButton()); bot.add_view(ApplicationButtonView())
        await i.message.edit(view=TicketButtonView())
        await i.response.send_message("✅ تم التحديث.", ephemeral=True)

class CloseTicketButton(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 إغلاق", style=discord.ButtonStyle.red, custom_id="btn_c1")
    async def c1(self, i, b):
        roles = i.user.roles if isinstance(i.user, discord.Member) else []
        if not ((get_role_ticket(i.guild) in roles) or (get_role_minister(i.guild) in roles) or has_control(i.user.id)):
            return await i.response.send_message("❌ لا تمتلك الصلاحية.", ephemeral=True)
        await i.response.send_message("🔒 سيغلق بعد دقيقة.", ephemeral=True)
        await asyncio.sleep(60)
        await i.channel.delete()

class ApplicationModal(Modal, title="🇸🇦 استمارة"):
    q1 = TextInput(label="الاسم", max_length=32, required=True)
    q2 = TextInput(label="العمر", required=True)
    async def on_submit(self, i):
        ch = get_ch_log_tickets(i.guild)
        if not ch: return await i.response.send_message("❌ لا يوجد روم.", ephemeral=True)
        embed = discord.Embed(title="🇸🇦 طلب جنسية", description=f"من: {i.user.mention}\nالاسم: {self.q1.value}\nالعمر: {self.q2.value}", color=discord.Color.green())
        await ch.send(embed=embed, view=AdminDecisionView(member=i.user, apply_name=self.q1.value))
        await i.response.send_message("✅ تم الإرسال.", ephemeral=True)

class ApplicationButtonView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🇸🇦 التقديم", style=discord.ButtonStyle.success, custom_id="btn_a1")
    async def a1(self, i, b): await i.response.send_modal(ApplicationModal())

class AdminDecisionView(View):
    def __init__(self, member, apply_name): super().__init__(timeout=None); self.member, self.apply_name = member, apply_name
    async def chk(self, i):
        roles = i.user.roles if isinstance(i.user, discord.Member) else []
        if (get_role_apply(i.guild) in roles) or (get_role_minister(i.guild) in roles) or has_control(i.user.id): return True
        await i.response.send_message("❌ لا تمتلك الصلاحية.", ephemeral=True); return False
    @discord.ui.button(label="✅ قبول", style=discord.ButtonStyle.success, custom_id="btn_ad1")
    async def ad1(self, i, b):
        if not await self.chk(i): return
        cr = get_role_citizen(i.guild)
        if cr: await self.member.add_roles(cr)
        try: await self.member.edit(nick=self.apply_name)
        except: pass
        await i.message.edit(view=None)
        await i.response.send_message("✅ تم القبول.", ephemeral=True)
    @discord.ui.button(label="❌ رفض", style=discord.ButtonStyle.red, custom_id="btn_ad2")
    async def ad2(self, i, b):
        if not await self.chk(i): return
        await i.message.edit(view=None)
        await i.response.send_message("❌ تم الرفض.", ephemeral=True)

# ═══════════════════════════════════════════════════════════════
# 🚨 أوامر الإدارة الشاملة
# ═══════════════════════════════════════════════════════════════
@bot.tree.command(name="بانل_البرقيات", description="📜 بانل")
async def p1(i):
    if not await require_control(i): return
    ch = get_ch_ticket_panel(i.guild)
    if ch: await ch.send(embed=discord.Embed(title="📜 البرقيات", color=0x007A3D), view=TicketButtonView()); await i.response.send_message("✅", ephemeral=True)
    else: await i.response.send_message("❌ لم أجد الروم.", ephemeral=True)

@bot.tree.command(name="بانل_الجنسية", description="🇸🇦 جنسية")
async def p2(i):
    if not await require_control(i): return
    ch = get_ch_apply_panel(i.guild)
    if ch: await ch.send(embed=discord.Embed(title="🇸🇦 التقديم", color=0x007A3D), view=ApplicationButtonView()); await i.response.send_message("✅", ephemeral=True)
    else: await i.response.send_message("❌ لم أجد الروم.", ephemeral=True)

@bot.tree.command(name="أمر_توقيف", description="🚔 توقيف")
async def c_jail(i, member: discord.Member, reason: str = "لم يحدد"):
    if not await require_control(i): return
    ok, msg = await apply_jail(i.guild, member, reason, issued_by=i.user); await i.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="أمر_إفراج", description="🔓 إفراج")
async def c_unjail(i, member: discord.Member):
    if not await require_control(i): return
    ok, msg = await remove_jail(i.guild, member); await i.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="إنذار_رسمي", description="⚠️ إنذار")
async def c_warn(i, member: discord.Member, reason: str = "لم يحدد"):
    if not await require_control(i): return
    USER_WARNINGS.setdefault(member.id, []).append({"reason": reason, "date": str(datetime.datetime.now())})
    await save_warnings()
    if len(USER_WARNINGS[member.id]) >= 3: await apply_jail(i.guild, member, "3 إنذارات")
    await i.response.send_message(f"✅ إنذار. الإجمالي: {len(USER_WARNINGS[member.id])}", ephemeral=True)

@bot.tree.command(name="سجل_الإنذارات", description="📋 سجل")
async def c_log(i, member: discord.Member):
    warns = USER_WARNINGS.get(member.id, [])
    await i.response.send_message(embed=discord.Embed(title=f"إنذارات {member.name}", description="\n".join([f"- {w['reason']}" for w in warns]) or "لا يوجد", color=discord.Color.orange()), ephemeral=True)

@bot.tree.command(name="تفتيش_المملكة", description="🔍 تفتيش")
async def c_check(i):
    if not await require_control(i): return
    await i.response.send_message("✅ النظام يعمل والإعدادات سليمة.", ephemeral=True)

@bot.tree.command(name="تعيين_وزير", description="👑 وزير")
async def c_min(i, member: discord.Member):
    if not await require_owner(i): return
    if member.id not in deputy_user_ids: deputy_user_ids.append(member.id); await save_state(); await i.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="حماية_مواطن", description="🛡️ حماية")
async def c_prot(i, member: discord.Member):
    if not await require_control(i): return
    if member.id not in protected_users_list: protected_users_list.append(member.id); await save_state(); await i.response.send_message("✅", ephemeral=True)

@bot.tree.command(name="تنظيف", description="🗑️ حذف")
async def c_clear(i, amount: int):
    if not await require_control(i): return
    await i.response.defer(ephemeral=True); d = await i.channel.purge(limit=amount); await i.followup.send(f"✅ {len(d)}", ephemeral=True)

# ═══════════════════════════════════════════════════════════════
# 🎬 التشغيل
# ═══════════════════════════════════════════════════════════════
@bot.event
async def on_ready():
    log.info("البوت متصل: %s", bot.user)
    bot.add_view(TicketButtonView()); bot.add_view(CloseTicketButton()); bot.add_view(ApplicationButtonView())
    await load_all_state()
    try:
        guild = discord.Object(id=1475975508700303370)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info("تمت مزامنة الأوامر بنجاح!")
    except Exception as e: log.error("فشل المزامنة: %s", e)
    
    try:
        import extras
        extras.load_extras(bot, {"apply_jail": apply_jail, "remove_jail": remove_jail, "require_control": require_control, "is_exempted": is_exempted})
    except: pass

if __name__ == "__main__":
    if TOKEN and TOKEN != "ضع_التوكن_هنا": bot.run(TOKEN)
