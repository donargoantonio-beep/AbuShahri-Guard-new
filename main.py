import os
import asyncio
import datetime
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from keep_alive import keep_alive
from google import genai

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# تهيئة عميل الذكاء الاصطناعي
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) 

saved_roles = {}
protected_users_list = []      
protected_roles_list = []      
deputy_user_ids = []           

# ==================== إعدادات مالك البوت ====================
BOT_OWNER_ID = 813236200142929950
# ========================================================

VOICE_CHANNEL_ID = 0  

BAD_WORDS = [
    "كلب", "حمار", "قحبة", "زق", "خرا", "شمهور", "يعور", "لعنة", "قحط",
    "fuck", "shit", "bitch", "asshole", "dick", "bastard", "cunt", "pussy"
] 
SPAM_TRACKER = {}

RULES_TEXT = """
📜 **قوانين وعقوبات السيرفر:**

1. **السب والشتم والألفاظ النابية:** يمنع منعاً باتاً (عقوبة: تحويل لرتبة محجور).
2. **إرسال الروابط والدعوات الخارجية:** غير مسموح (عقوبة: تايم آوت ساعة).
3. **السبام وتكرار الرسائل:** غير مسموح (عقوبة: تايم آوت ساعة).
4. **الاحترام المتبادل:** يرجى احترام جميع الأعضاء لتجنب العقوبات.

نتمنى لك وقتاً ممتعاً معنا! 🌹
"""

async def check_owner_or_deputy_perm(interaction: discord.Interaction):
    if interaction.user.id == BOT_OWNER_ID or interaction.user.id in deputy_user_ids:
        return True
    if BOT_OWNER_ID == 0 and interaction.user.id == interaction.guild.owner_id:
        return True
    
    await interaction.response.send_message(
        "❌ عذراً، هذه الصلاحيات مخصصة لمالك البوت والنواب فقط.", 
        ephemeral=True
    )
    return False

def is_exempted(member: discord.Member):
    if member.id == BOT_OWNER_ID or member.id in deputy_user_ids or member.id == member.guild.owner_id:
        return True
    if member.id in protected_users_list:
        return True
    for role in member.roles:
        if role.id in protected_roles_list:
            return True
    return False

# ==================== أوامر الإرسال (إعلان / رسالة روم / رسالة خاص) ====================

@bot.tree.command(name="إعلان", description="إرسال إعلان رسمي (Embed) إلى روم محدد")
@discord.app_commands.describe(channel="الروم المراد إرسال الإعلان إليه", title="عنوان الإعلان", content="محتوى الإعلان")
async def announce(interaction: discord.Interaction, channel: discord.TextChannel, title: str, content: str):
    if not await check_owner_or_deputy_perm(interaction):
        return
    embed = discord.Embed(title=f"📢 {title}", description=content, color=discord.Color.red(), timestamp=discord.utils.utcnow())
    embed.set_footer(text=f"إعلان إداري | بواسطة: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ تم إرسال الإعلان بنجاح إلى {channel.mention}.", ephemeral=True)

@bot.tree.command(name="رسالة_روم", description="إرسال رسالة عادية باسم البوت إلى روم محدد")
@discord.app_commands.describe(channel="الروم", message="الرسالة")
async def send_to_channel(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not await check_owner_or_deputy_perm(interaction):
        return
    await channel.send(message)
    await interaction.response.send_message(f"✅ تم إرسال الرسالة إلى {channel.mention}.", ephemeral=True)

@bot.tree.command(name="رسالة_خاصة", description="إرسال رسالة بالخاص لعضو معين باسم البوت")
@discord.app_commands.describe(member="العضو", message="الرسالة")
async def send_dm_to_user(interaction: discord.Interaction, member: discord.Member, message: str):
    if not await check_owner_or_deputy_perm(interaction):
        return
    try:
        embed = discord.Embed(title="📩 رسالة من الإدارة", description=message, color=discord.Color.blue())
        embed.set_footer(text=f"مرسلة من سيرفر: {interaction.guild.name}")
        await member.send(embed=embed)
        await interaction.response.send_message(f"✅ تم إرسال الرسالة إلى {member.mention} بالخاص بنجاح.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ عذراً، لا يمكنني إرسال رسالة لـ {member.mention} لأن الخاص لديه مغلق.", ephemeral=True)

# ==================== الترحيب والقوانين بالخاص ====================

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    
    try:
        dm_embed = discord.Embed(
            title=f"أهلاً بك في {guild.name}! 🌟",
            description=RULES_TEXT,
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        print(f"⚠️ لم أتمكن من إرسال القوانين بالخاص للعضو {member.name} (مغلق الخاص)")

    channel = discord.utils.get(guild.text_channels, name="الترحيب〢✋🏻")
    if channel:
        embed = discord.Embed(
            title="🎉 عضو جديد انضم إلينا!",
            description=f"مرحباً بك {member.mention} في **{guild.name}**!\nنتمنى لك قضاء وقت ممتع معنا.",
            color=discord.Color.brand_green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=member.mention, embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name="دخول_خروج-💿") or discord.utils.get(member.guild.text_channels, name="دخول_خروج")
    if channel:
        embed = discord.Embed(title="📤 عضو غادر السيرفر", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        await channel.send(embed=embed)

# ==================== نظام الحماية ورتبة محجور ====================

async def punish_saboteur(member: discord.Member, reason: str):
    guild = member.guild
    try:
        # البحث عن رتبة محجور المجهزة مسبقاً
        jail_role = discord.utils.get(guild.roles, name="محجور")
        if not jail_role:
            print("⚠️ تنبيه: لم يتم العثور على رتبة باسم 'محجور' في السيرفر!")
            return

        jail_channel = discord.utils.get(guild.text_channels, name="quarantine-zone")
        if not jail_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                jail_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }
            jail_channel = await guild.create_text_channel("quarantine-zone", overwrites=overwrites)
        else:
            await jail_channel.set_permissions(jail_role, view_channel=True, send_messages=True, read_message_history=True)
            await jail_channel.set_permissions(guild.default_role, view_channel=False)

        saved_roles[member.id] = [r for r in member.roles if r != guild.default_role and r != jail_role]
        await member.edit(roles=[jail_role], reason=reason)

        log_channel = discord.utils.get(guild.text_channels, name="لوق_الحذف-💿") or discord.utils.get(guild.text_channels, name="admin-review")
        if log_channel:
            embed = discord.Embed(title="🚨 تم رصد مخالفة وتحويل العضو إلى محجور", color=discord.Color.red())
            embed.add_field(name="المخالف", value=member.mention, inline=False)
            embed.add_field(name="السبب", value=reason, inline=False)
            embed.description = "تم إعطاؤه رتبة **محجور** وسحب باقي الرتب تلقائياً."
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"❌ خطأ أثناء تطبيق الحجر: {e}")

@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    guild = channel.guild
    attacker = None
    
    await asyncio.sleep(0.5)
    try:
        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_delete):
            if entry.target and entry.target.id == channel.id:
                attacker = entry.user
                break
    except Exception as e:
        print(f"⚠️ خطأ أثناء قراءة سجلات الحذف: {e}")

    if attacker and (attacker.bot or is_exempted(attacker)):
        return

    try:
        if isinstance(channel, discord.TextChannel):
            await guild.create_text_channel(name=channel.name, category=channel.category, overwrites=channel.overwrites, topic=channel.topic, position=channel.position)
        elif isinstance(channel, discord.VoiceChannel):
            await guild.create_voice_channel(name=channel.name, category=channel.category, overwrites=channel.overwrites, bitrate=channel.bitrate, user_limit=channel.user_limit, position=channel.position)
        elif isinstance(channel, discord.StageChannel):
            await guild.create_stage_channel(name=channel.name, category=channel.category, overwrites=channel.overwrites, position=channel.position)
    except Exception as e:
        print(f"❌ فشل إعادة إنشاء الروم: {e}")

    if attacker:
        try:
            member = guild.get_member(attacker.id)
            if member:
                await punish_saboteur(member, "حذف روم بدون صلاحية")
        except:
            pass

@bot.event
async def on_guild_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    guild = after.guild
    attacker = None
    
    await asyncio.sleep(0.5)
    try:
        async for entry in guild.audit_logs(limit=3, action=discord.AuditLogAction.channel_update):
            if entry.target and entry.target.id == after.id:
                attacker = entry.user
                break
    except:
        pass

    if attacker and (attacker.bot or is_exempted(attacker)):
        return

    try:
        if before.overwrites != after.overwrites:
            await after.edit(overwrites=before.overwrites, reason="محاولة تخريب الصلاحيات")
            if attacker:
                member = guild.get_member(attacker.id)
                if member:
                    await punish_saboteur(member, "تخريب صلاحيات الرومات")
    except:
        pass

# ==================== نظام الذكاء الاصطناعي والشات التلقائي ====================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    # روم الذكاء الاصطناعي
    if "ai-ymym" in message.channel.name.lower():
        ai_role = discord.utils.get(message.guild.roles, name="Ai ymym")
        has_permission = False
        
        if is_exempted(message.author):
            has_permission = True
        elif ai_role and ai_role in message.author.roles:
            has_permission = True

        if not has_permission:
            try:
                await message.delete()
                warning = await message.channel.send(f"❌ {message.author.mention} هذا الروم للرتبة **Ai ymym** فقط.")
                await asyncio.sleep(5)
                await warning.delete()
            except:
                pass
            return

        async with message.channel.typing():
            try:
                response = ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"أنت مساعد ذكي ومطور خبير للبوت الخاص بالسيرفر. المالك هو أبو شهري. أجب باحترافية على: {message.content}"
                )
                
                ai_reply = response.text if response and response.text else "عذراً، حدث خطأ في الرد."
                
                if len(ai_reply) > 2000:
                    for i in range(0, len(ai_reply), 2000):
                        await message.reply(ai_reply[i:i+2000])
                else:
                    await message.reply(ai_reply)
                    
            except Exception as e:
                await message.reply(f"❌ خطأ: `{e}`")
        return

    # حماية الشات العادي
    if is_exempted(message.author):
        await bot.process_commands(message)
        return

    content_lower = message.content.lower()
    violation_type = None
    action_taken = None

    for word in BAD_WORDS:
        if word in content_lower:
            violation_type = "سب وشتم / ألفاظ نابية"
            action_taken = "إعطاء رتبة محجور وحذف الرسالة"
            break

    if not violation_type:
        if "http://" in content_lower or "https://" in content_lower or "discord.gg/" in content_lower:
            violation_type = "إرسال روابط خارجية"
            action_taken = "تايم آوت ساعة وحذف الرسالة"

    if not violation_type:
        user_id = message.author.id
        import time
        current_time = time.time()
        
        if user_id in SPAM_TRACKER:
            last_msg, last_time = SPAM_TRACKER[user_id]
            if message.content == last_msg and (current_time - last_time) < 3:
                violation_type = "سبام وتكرار سريع"
                action_taken = "تايم آوت ساعة وحذف الرسالة"
        SPAM_TRACKER[user_id] = (message.content, current_time)

    if violation_type:
        guild = message.guild
        admin_channel = discord.utils.get(guild.text_channels, name="admin-review")

        try:
            await message.delete()
        except:
            pass

        if "محجور" in action_taken:
            await punish_saboteur(message.author, "تجاوز أخلاقي في الشات (سب وشتم)")
        else:
            try:
                duration = datetime.timedelta(hours=1)
                await message.author.timeout(duration, reason=violation_type)
            except:
                pass

        embed = discord.Embed(title="🚨 رصد مخالفة شات", color=discord.Color.red())
        embed.add_field(name="المخالف", value=f"{message.author.mention}", inline=True)
        embed.add_field(name="المخالفة", value=violation_type, inline=True)
        embed.add_field(name="الإجراء", value=action_taken, inline=True)
        embed.add_field(name="المحتوى", value=message.content or "*(وسائط)*", inline=False)

        if admin_channel:
            await admin_channel.send(embed=embed)
        return

    await bot.process_commands(message)

# ==================== الأزرار والتذاكر والتقديم ====================

class ApplicationModal(Modal, title="نموذج التقديم للإدارة"):
    q1 = TextInput(label="الاسم", placeholder="اكتب اسمك هنا...", required=True)
    q2 = TextInput(label="العمر", placeholder="اكتب عمرك...", required=True)
    q3 = TextInput(label="لماذا تريد الانضمام للإدارة؟", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        admin_channel = discord.utils.get(interaction.guild.text_channels, name="admin-review")
        if not admin_channel:
            await interaction.response.send_message("❌ لم يتم العثور على روم المراجعة.", ephemeral=True)
            return
        embed = discord.Embed(title="📥 طلب تقديم جديد", color=discord.Color.gold())
        embed.add_field(name="المتقدم", value=interaction.user.mention, inline=False)
        embed.add_field(name="الاسم", value=self.q1.value, inline=False)
        embed.add_field(name="العمر", value=self.q2.value, inline=False)
        embed.add_field(name="السبب", value=self.q3.value, inline=False)
        await admin_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم إرسال تقديمك بنجاح!", ephemeral=True)

class ApplicationButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="تقديم على الإدارة", style=discord.ButtonStyle.green, custom_id="apply_btn_perm")
    async def apply_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModal())

class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_perm")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("⏳ جاري الإغلاق...", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete()

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 🎫", style=discord.ButtonStyle.primary, custom_id="open_ticket_perm")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="التذاكر") or await guild.create_category("التذاكر")
        ticket_channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name.lower()}", 
            category=category, 
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
        )
        embed = discord.Embed(title="تذكرة دعم فني", description="فريق الدعم سيقوم بالرد عليك قريباً.", color=discord.Color.blue())
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketButton())
        await interaction.response.send_message(f"✅ تذكرتك: {ticket_channel.mention}", ephemeral=True)

# ==================== الأوامر الإدارية الأساسية ====================

@bot.tree.command(name="مسح", description="مسح عدد معين من الرسائل")
async def clear_messages(interaction: discord.Interaction, amount: int):
    if not await check_owner_or_deputy_perm(interaction): return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=min(amount, 100))
    await interaction.followup.send(f"✅ تم مسح `{len(deleted)}` رسالة.", ephemeral=True)

@bot.tree.command(name="تعيين_نائب", description="إضافة نائب")
async def add_deputy(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != BOT_OWNER_ID: return await interaction.response.send_message("❌ للمالك فقط.", ephemeral=True)
    if member.id not in deputy_user_ids: deputy_user_ids.append(member.id)
    await interaction.response.send_message(f"✅ تم تعيين {member.mention} نائب.", ephemeral=True)

@bot.tree.command(name="إزالة_نائب", description="إزالة نائب")
async def remove_deputy(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != BOT_OWNER_ID: return await interaction.response.send_message("❌ للمالك فقط.", ephemeral=True)
    if member.id in deputy_user_ids: deputy_user_ids.remove(member.id)
    await interaction.response.send_message(f"✅ تم إزالة {member.mention}.", ephemeral=True)

@bot.tree.command(name="حماية_شخص", description="إضافة شخص للحماية")
async def protect_person(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction): return
    if member.id not in protected_users_list: protected_users_list.append(member.id)
    await interaction.response.send_message(f"🛡️ تمت حماية {member.mention}.", ephemeral=True)

@bot.tree.command(name="إزالة_حماية_شخص", description="إزالة شخص من الحماية")
async def unprotect_person(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction): return
    if member.id in protected_users_list: protected_users_list.remove(member.id)
    await interaction.response.send_message(f"🔓 تمت إزالة حماية {member.mention}.", ephemeral=True)

@bot.tree.command(name="حماية_رتبه", description="إضافة رتبة للحماية")
async def protect_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_owner_or_deputy_perm(interaction): return
    if role.id not in protected_roles_list: protected_roles_list.append(role.id)
    await interaction.response.send_message(f"🛡️ تمت حماية {role.mention}.", ephemeral=True)

@bot.tree.command(name="إزالة_حماية_رتبه", description="إزالة رتبة من الحماية")
async def unprotect_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_owner_or_deputy_perm(interaction): return
    if role.id in protected_roles_list: protected_roles_list.remove(role.id)
    await interaction.response.send_message(f"🔓 أزيلت الحماية عن {role.mention}.", ephemeral=True)

@bot.tree.command(name="قائمة_الحماية", description="عرض النواب والمحميين")
async def protection_dashboard(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ لوحة الحماية", color=discord.Color.gold())
    embed.add_field(name="الأشخاص", value="\n".join([f"<@{u}>" for u in protected_users_list]) or "لا يوجد", inline=False)
    embed.add_field(name="الرتب", value="\n".join([f"<@&{r}>" for r in protected_roles_list]) or "لا يوجد", inline=False)
    embed.add_field(name="النواب", value="\n".join([f"<@{u}>" for u in deputy_user_ids]) or "لا يوجد", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="اعداد_الرومات_الاساسيه", description="إنشاء رومات النظام الأساسية")
async def setup(interaction: discord.Interaction):
    if not await check_owner_or_deputy_perm(interaction): return
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if not discord.utils.get(guild.roles, name="Ai ymym"): await guild.create_role(name="Ai ymym", color=discord.Color.teal())
    
    ai_ch = discord.utils.get(guild.text_channels, name="💭〢ai-ymym-chat") or await guild.create_text_channel("💭〢ai-ymym-chat")
    await ai_ch.send(embed=discord.Embed(title="🤖 محادثة AI", description="للأشخاص المسموح لهم فقط.", color=discord.Color.blurple()))

    tk_ch = discord.utils.get(guild.text_channels, name="الدعم-الفني🎫") or await guild.create_text_channel("الدعم-الفني🎫")
    await tk_ch.send(embed=discord.Embed(title="مركز الدعم", description="افتح تذكرة من هنا"), view=TicketButtonView())

    ap_ch = discord.utils.get(guild.text_channels, name="التقديم-للسيرفر") or await guild.create_text_channel("التقديم-للسيرفر")
    await ap_ch.send(embed=discord.Embed(title="التقديم للإدارة", description="اضغط هنا للتقديم"), view=ApplicationButtonView())

    await interaction.followup.send("✅ تم إعداد الرومات!", ephemeral=True)

@bot.tree.command(name="روم_صوتي", description="ربط البوت بروم صوتي دائم")
async def voice_command(interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
    if not await check_owner_or_deputy_perm(interaction): return
    global VOICE_CHANNEL_ID
    VOICE_CHANNEL_ID = voice_channel.id
    if interaction.guild.me.voice: await interaction.guild.me.voice.channel.disconnect()
    await voice_channel.connect()
    await interaction.response.send_message(f"✅ تم الربط بـ {voice_channel.mention}", ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    global VOICE_CHANNEL_ID
    if VOICE_CHANNEL_ID != 0 and member.id == bot.user.id:
        if before.channel and before.channel.id == VOICE_CHANNEL_ID and (after.channel is None or after.channel.id != VOICE_CHANNEL_ID):
            await asyncio.sleep(1)
            try:
                await member.guild.get_channel(VOICE_CHANNEL_ID).connect()
            except:
                pass

@bot.tree.command(name="المالك", description="عرض معلومات مالك البوت")
async def owner_info(interaction: discord.Interaction):
    embed = discord.Embed(title="👑 معلومات مالك البوت", color=discord.Color.purple())
    embed.add_field(name="الاسم", value="Abo Shehri", inline=False)
    embed.add_field(name="المعرف", value="`ii.ih`", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    bot.add_view(TicketButtonView())
    bot.add_view(CloseTicketButton())
    bot.add_view(ApplicationButtonView())
    await bot.tree.sync()
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    
    if VOICE_CHANNEL_ID != 0:
        for guild in bot.guilds:
            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if channel and isinstance(channel, discord.VoiceChannel):
                try: await channel.connect()
                except: pass

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
