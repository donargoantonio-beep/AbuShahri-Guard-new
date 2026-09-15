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
BOT_OWNER_ID = 813236200142929950  # <--- آيديك الأساسي
# ========================================================

VOICE_CHANNEL_ID =  

BAD_WORDS = [
    "كلب", "حمار", "قحبة", "زق", "خرا", "شمهور", "يعور", "لعنة", "قحط",
    "fuck", "shit", "bitch", "asshole", "dick", "bastard", "cunt", "pussy"
] 
SPAM_TRACKER = {}

RULES_TEXT = """
📜 **قوانين وعقوبات سيرفرنا:**

1. **السب والشتم والألفاظ النابية (عربي / إنجليزي):**
   • *العقوبة:* **وضع العضو في الحجر فوراً** مع سحب الرتب المؤقتة وإرسال التقرير للإدارة.
2. **إرسال الروابط والدعوات الخارجية:**
   • *العقوبة:* **تايم آوت (Timeout) لمدة ساعة كاملة** + حذف الرسالة.
3. **السبام وتكرار الرسائل أو الحروف:**
   • *العقوبة:* **تايم آوت (Timeout) لمدة ساعة كاملة** + حذف الرسالة.
4. **عدم احترام الجميع وإثارة المشاكل:**
   • *العقوبة:* تايم آوت لمدة ساعة أو تصعيد العقوبة.

يرجى الالتزام التام بالقوانين لتجنب العقوبات الإدارية.
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

# ==================== نظام الحماية الشامل ضد النيوك والتخريب ====================

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
        except Exception as e:
            print(f"❌ خطأ أثناء معاقبة المخالف: {e}")

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
    except Exception as e:
        print(f"⚠️ خطأ في قراءة سجلات تعديل الرومات: {e}")

    if attacker and (attacker.bot or is_exempted(attacker)):
        return

    try:
        if before.overwrites != after.overwrites:
            await after.edit(overwrites=before.overwrites, reason="محاولة تخريب الصلاحيات")
            if attacker:
                member = guild.get_member(attacker.id)
                if member:
                    await punish_saboteur(member, "تخريب صلاحيات الرومات")
    except Exception as e:
        print(f"❌ خطأ في معالجة تعديل الروم: {e}")

async def punish_saboteur(member: discord.Member, reason: str):
    guild = member.guild
    try:
        jail_role = discord.utils.get(guild.roles, name="قوانين-الحجر")
        if not jail_role:
            jail_role = await guild.create_role(name="قوانين-الحجر", color=discord.Color.dark_grey())
            
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
            embed = discord.Embed(title="🚨 تم رصد محاولة تخريب (نيوك / عبث)", color=discord.Color.red())
            embed.add_field(name="المخالف", value=member.mention, inline=False)
            embed.add_field(name="السبب", value=reason, inline=False)
            embed.description = "تمت معاقبته وتحويله للحجر تلقائياً وإلغاء التخريب."
            await log_channel.send(embed=embed)
    except Exception as e:
        print(f"❌ خطأ في معاقبة المخالف: {e}")


# ==================== نظام الذكاء الاصطناعي المحدث (Ai ymym) ====================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

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
                warning_msg = await message.channel.send(f"❌ {message.author.mention} عذراً، هذا الروم مخصص فقط لمن يمتلك رتبة **Ai ymym**.")
                await asyncio.sleep(5)
                await warning_msg.delete()
            except:
                pass
            return

        async with message.channel.typing():
            try:
                # استخدام الموديل المحدث المطلوب من قِبل واجهة برمجة التطبيقات
                response = ai_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=f"أنت مساعد ذكي ومطور خبير للبوت الخاص بالسيرفر. المالك هو أبو شهري. أجب باحترافية على سؤال المستخدم التالي:\n\n{message.content}"
                )
                
                ai_reply = response.text if response and response.text else "عذراً، لم أتمكن من صياغة إجابة."
                
                if len(ai_reply) > 2000:
                    for i in range(0, len(ai_reply), 2000):
                        await message.reply(ai_reply[i:i+2000])
                else:
                    await message.reply(ai_reply)
                    
            except Exception as e:
                print(f"⚠️ خطأ في معالجة الذكاء الاصطناعي: {e}")
                await message.reply(f"❌ حدث خطأ في النظام: `{e}`")
        return

    if is_exempted(message.author):
        await bot.process_commands(message)
        return

    content_lower = message.content.lower()
    violation_type = None
    action_taken = None

    for word in BAD_WORDS:
        if word in content_lower:
            violation_type = "السب والشتم / ألفاظ نابية (عربي أو إنجليزي)"
            action_taken = "وضع العضو في الحجر وحذف الرسالة"
            break

    if not violation_type:
        if "http://" in content_lower or "https://" in content_lower or "discord.gg/" in content_lower or "www." in content_lower:
            violation_type = "إرسال روابط غير مصرح بها"
            action_taken = "تايم آوت لمدة ساعة وحذف الرسالة"

    if not violation_type:
        user_id = message.author.id
        import time
        current_time = time.time()
        
        if user_id in SPAM_TRACKER:
            last_msg, last_time = SPAM_TRACKER[user_id]
            if message.content == last_msg and (current_time - last_time) < 3:
                violation_type = "السبام وتكرار الرسائل بسرعة"
                action_taken = "تايم آوت لمدة ساعة وحذف الرسالة"
        SPAM_TRACKER[user_id] = (message.content, current_time)

    if violation_type:
        guild = message.guild
        admin_channel = discord.utils.get(guild.text_channels, name="admin-review")

        try:
            await message.delete()
        except:
            pass

        if "الحجر" in action_taken:
            try:
                jail_role = discord.utils.get(guild.roles, name="قوانين-الحجر")
                if not jail_role:
                    jail_role = await guild.create_role(name="قوانين-الحجر", color=discord.Color.dark_grey())
                    
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

                saved_roles[message.author.id] = [r for r in message.author.roles if r != guild.default_role and r != jail_role]
                await message.author.edit(roles=[jail_role], reason="استخدام ألفاظ نابية / سب وشتم")
            except Exception as e:
                print(f"❌ خطأ في تطبيق الحجر: {e}")
        else:
            try:
                duration = datetime.timedelta(hours=1)
                await message.author.timeout(duration, reason=f"مخالفة الشات: {violation_type}")
            except Exception as e:
                print(f"❌ خطأ في تطبيق التايم آوت: {e}")

        embed = discord.Embed(
            title="🚨 رصد مخالفة في الشات وتم اتخاذ الإجراء",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
        embed.add_field(name="العضو المخالف", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
        embed.add_field(name="السيرفر", value=guild.name, inline=True)
        embed.add_field(name="الروم", value=message.channel.mention, inline=True)
        embed.add_field(name="نوع المخالفة", value=violation_type, inline=True)
        embed.add_field(name="الإجراء المتخذ", value=action_taken, inline=True)
        embed.add_field(name="محتوى الرسالة المخالفة", value=message.content or "*(وسائط أو محتوى فارغ)*", inline=False)

        if admin_channel:
            await admin_channel.send(embed=embed)

        try:
            owner_user = await bot.fetch_user(BOT_OWNER_ID)
            if owner_user:
                await owner_user.send(embed=embed)
        except Exception as e:
            print(f"⚠️ تعذر إرسال إشعار المخالفة لخاص المالك: {e}")

        return

    await bot.process_commands(message)


# ==================== الترحيب واللوقات ====================

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
        pass

    channel = discord.utils.get(guild.text_channels, name="الترحيب〢✋🏻")
    if channel:
        embed = discord.Embed(
            title=f"أهلاً بك في {guild.name}! 🎉",
            description=f"مرحباً بك {member.mention} في سيرفرنا!",
            color=discord.Color.brand_green(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name="دخول_خروج-💿") or discord.utils.get(member.guild.text_channels, name="دخول_خروج")
    if channel:
        embed = discord.Embed(title="📤 عضو غادر السيرفر", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        await channel.send(embed=embed)


# ==================== الأزرار والتذاكر والتقديم ====================

class ApplicationModal(Modal, title="نموذج التقديم للإدارة"):
    q1 = TextInput(label="الاسم", placeholder="اكتب اسمك هنا...", required=True)
    q2 = TextInput(label="العمر", placeholder="اكتب عمرك...", required=True)
    q3 = TextInput(label="ما هو سبب دخولك للسيرفر؟", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        admin_channel = discord.utils.get(interaction.guild.text_channels, name="admin-review")
        if not admin_channel:
            await interaction.response.send_message("❌ لم يتم العثور على روم المراجعة.", ephemeral=True)
            return
        embed = discord.Embed(title="📥 طلب تقديم جديد", color=discord.Color.gold())
        embed.add_field(name="المتقدم", value=interaction.user.mention, inline=False)
        embed.add_field(name="الاسم", value=self.q1.value, inline=False)
        embed.add_field(name="العمر", value=self.q2.value, inline=False)
        embed.add_field(name="سبب الدخول", value=self.q3.value, inline=False)
        await admin_channel.send(embed=embed)
        await interaction.response.send_message("✅ تم إرسال تقديمك بنجاح للإدارة!", ephemeral=True)

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
        await interaction.response.send_message("⏳ جاري إغلاق التذكرة...", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete()

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="فتح تذكرة 🎫", style=discord.ButtonStyle.primary, custom_id="open_ticket_perm")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="التذاكر") or await guild.create_category("التذاكر")
        channel_name = f"ticket-{interaction.user.name.lower()}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        embed = discord.Embed(title="تذكرة جديدة", description="يرجى كتابة مشكلتك وسيقوم فريق الدعم بالرد.", color=discord.Color.blue())
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketButton())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك: {ticket_channel.mention}", ephemeral=True)


# ==================== الأوامر الإدارية والنظامية ====================

@bot.tree.command(name="مسح", description="مسح عدد معين من الرسائل")
@discord.app_commands.describe(amount="عدد الرسائل المراد مسحها")
async def clear_messages(interaction: discord.Interaction, amount: int):
    if not await check_owner_or_deputy_perm(interaction):
        return
    if amount > 100:
        amount = 100
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"✅ تم مسح `{len(deleted)}` رسالة بنجاح.", ephemeral=True)

@bot.tree.command(name="تعيين_نائب", description="[مالك البوت فقط] إضافة نائب")
async def add_deputy(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("❌ عذراً، هذا الأمر للمالك فقط.", ephemeral=True)
        return
    if member.id not in deputy_user_ids:
        deputy_user_ids.append(member.id)
        await interaction.response.send_message(f"✅ تم تعيين {member.mention} كنائب للبوت.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} نائب بالفعل.", ephemeral=True)

@bot.tree.command(name="إزالة_نائب", description="[مالك البوت فقط] إزالة نائب")
async def remove_deputy(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != BOT_OWNER_ID:
        await interaction.response.send_message("❌ عذراً، هذا الأمر للمالك فقط.", ephemeral=True)
        return
    if member.id in deputy_user_ids:
        deputy_user_ids.remove(member.id)
        await interaction.response.send_message(f"✅ تم إزالة {member.mention} من النواب.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ {member.mention} ليس نائباً.", ephemeral=True)

@bot.tree.command(name="حماية_شخص", description="إضافة شخص لقائمة الحماية الفردية")
async def protect_person(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction):
        return
    if member.id not in protected_users_list:
        protected_users_list.append(member.id)
        await interaction.response.send_message(f"🛡️ تمت إضافة {member.mention} لقائمة الحماية.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ العضو محمي مسبقاً.", ephemeral=True)

@bot.tree.command(name="إزالة_حماية_شخص", description="إزالة الحماية الفردية عن شخص")
async def unprotect_person(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction):
        return
    if member.id in protected_users_list:
        protected_users_list.remove(member.id)
        await interaction.response.send_message(f"🔓 تمت إزالة الحماية عن {member.mention}.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ العضو ليس في قائمة الحماية.", ephemeral=True)

@bot.tree.command(name="حماية_رتبه", description="إضافة رتبة إلى الرتب المحمية")
async def protect_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_owner_or_deputy_perm(interaction):
        return
    if role.id not in protected_roles_list:
        protected_roles_list.append(role.id)
        await interaction.response.send_message(f"🛡️ تمت إضافة الرتبة {role.mention} للرتب المحمية.", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ الرتبة محمية مسبقاً.", ephemeral=True)

@bot.tree.command(name="إزالة_حماية_رتبه", description="إزالة رتبة من الرتب المحمية")
async def unprotect_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_owner_or_deputy_perm(interaction):
        return
    if role.id in protected_roles_list:
        protected_roles_list.remove(role.id)
        await interaction.response.send_message(f"🔓 تمت إزالة الرتبة {role.mention} من الرتب المحمية.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ الرتبة ليست في قائمة الحماية.", ephemeral=True)

@bot.tree.command(name="قائمة_الحماية", description="عرض لوحة الحماية والنواب")
async def protection_dashboard(interaction: discord.Interaction):
    embed = discord.Embed(title="🛡️ لوحة معلومات الحماية", color=discord.Color.gold())
    users_text = "\n".join([f"• <@{uid}>" for uid in protected_users_list]) if protected_users_list else "لا يوجد"
    roles_text = "\n".join([f"• <@&{rid}>" for rid in protected_roles_list]) if protected_roles_list else "لا توجد"
    nawwab_text = "\n".join([f"• <@{uid}>" for uid in deputy_user_ids]) if deputy_user_ids else "لا يوجد"
    embed.add_field(name="👤 الأشخاص المحميين", value=users_text, inline=False)
    embed.add_field(name="👑 الرتب المحمية", value=roles_text, inline=False)
    embed.add_field(name="🛡️ النواب", value=nawwab_text, inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="اعداد_الرومات_الاساسيه", description="إنشاء رومات النظام الأساسية والتذاكر والتقديم والذكاء الاصطناعي")
async def setup(interaction: discord.Interaction):
    if not await check_owner_or_deputy_perm(interaction):
        return
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if not discord.utils.get(guild.roles, name="Ai ymym"):
        await guild.create_role(name="Ai ymym", color=discord.Color.teal())

    ai_channel = discord.utils.get(guild.text_channels, name="💭〢ai-ymym-chat") or await guild.create_text_channel("💭〢ai-ymym-chat")
    await ai_channel.send(embed=discord.Embed(title="🤖 محادثة الذكاء الاصطناعي (Ai ymym)", description="هذا الروم يتطلب رتبة Ai ymym للتفاعل.", color=discord.Color.blurple()))

    ticket_panel = discord.utils.get(guild.text_channels, name="الدعم-الفني🎫") or await guild.create_text_channel("الدعم-الفني🎫")
    await ticket_panel.send(embed=discord.Embed(title="مركز الدعم والتذاكر", description="اضغط لفتح تذكرة"), view=TicketButtonView())

    apply_panel = discord.utils.get(guild.text_channels, name="التقديم-للسيرفر") or await guild.create_text_channel("التقديم-للسيرفر")
    await apply_panel.send(embed=discord.Embed(title="التقديم لفريق الإدارة", description="اضغط لتعبئة الاستمارة"), view=ApplicationButtonView())

    await interaction.followup.send("✅ تم إعداد جميع الرومات والنظام بنجاح!", ephemeral=True)

@bot.tree.command(name="روم_صوتي", description="ربط البوم بروم صوتي دائم")
async def voice_command(interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
    if not await check_owner_or_deputy_perm(interaction):
        return
    global VOICE_CHANNEL_ID
    VOICE_CHANNEL_ID = voice_channel.id
    if interaction.guild.me.voice:
        await interaction.guild.me.voice.channel.disconnect()
    await voice_channel.connect()
    await interaction.response.send_message(f"✅ تم ربط الروم الصوتي الدائم بـ: **{voice_channel.name}**", ephemeral=True)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    global VOICE_CHANNEL_ID
    if VOICE_CHANNEL_ID == 0:
        return
    if member.id == bot.user.id:
        if before.channel and before.channel.id == VOICE_CHANNEL_ID and (after.channel is None or after.channel.id != VOICE_CHANNEL_ID):
            await asyncio.sleep(1)
            guild = member.guild
            channel = guild.get_channel(VOICE_CHANNEL_ID)
            if channel and isinstance(channel, discord.VoiceChannel):
                try:
                    await channel.connect()
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
                try:
                    await channel.connect()
                except:
                    pass

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
