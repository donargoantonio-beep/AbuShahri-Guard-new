import os
import asyncio
import datetime
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

saved_roles = {}
protected_users_list = []      
protected_roles_list = []      
deputy_user_ids = []           

# ==================== إعدادات مالك البوت ====================
BOT_OWNER_ID = 813236200142929950  # <--- آيديك الأساسي
# ========================================================

VOICE_CHANNEL_ID = 0  

BAD_WORDS = ["كلب", "حمار", "قحبة", "زق", "خرا", "شمهور", "يعور", "لعنة", "قحط"] 
SPAM_TRACKER = {}

# نص القوانين
RULES_TEXT = """📜 **قوانين وعقوبات السيرفر:**

1. **السب والشتم والألفاظ النابية:** يمنع منعاً باتاً (عقوبة: تحويل لرتبة محجور).
2. **إرسال الروابط والدعوات الخارجية:** غير مسموح (عقوبة: تايم آوت ساعة).
3. **السبام وتكرار الرسائل:** غير مسموح (عقوبة: تايم آوت ساعة).
4. **الاحترام المتبادل:** يرجى احترام جميع الأعضاء لتجنب العقوبات.

نتمنى لك وقتاً ممتعاً معنا! 🌹"""

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

# ==================== نظام الحماية الصارم لحذف الرومات ====================

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
                jail_role = discord.utils.get(guild.roles, name="محجور")
                if jail_role:
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
                    await member.edit(roles=[jail_role], reason="حذف روم بدون صلاحية")

                    log_delete = discord.utils.get(guild.text_channels, name="لوق_الحذف-💿") or discord.utils.get(guild.text_channels, name="لوق_الحذف")
                    if log_delete:
                        embed = discord.Embed(title="🚨 حذف روم غير مصرح به", color=discord.Color.red())
                        embed.add_field(name="المخالف", value=member.mention, inline=False)
                        embed.add_field(name="الروم المحذوف", value=channel.name, inline=False)
                        embed.description = "تمت معاقبته وإعطاؤه رتبة محجور وإعادة إنشاء الروم تلقائياً."
                        await log_delete.send(embed=embed)
        except Exception as e:
            print(f"❌ خطأ أثناء معاقبة المخالف: {e}")


# ==================== نظام المراقبة التلقائية للشات والعقوبات ====================

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if is_exempted(message.author):
        await bot.process_commands(message)
        return

    content_lower = message.content.lower()
    violation_type = None
    action_taken = None

    if any(word in content_lower for word in BAD_WORDS):
        violation_type = "السب والشتم / ألفاظ نابية"
        action_taken = "إعطاء العضو رتبة محجور"

    if not violation_type:
        if "http://" in content_lower or "https://" in content_lower or "discord.gg/" in content_lower or "www." in content_lower:
            violation_type = "إرسال روابط غير مصرح بها"
            action_taken = "تايم آوت لمدة ساعة"

    if not violation_type:
        user_id = message.author.id
        import time
        current_time = time.time()
        
        if user_id in SPAM_TRACKER:
            last_msg, last_time = SPAM_TRACKER[user_id]
            if message.content == last_msg and (current_time - last_time) < 3:
                violation_type = "السبام وتكرار الرسائل بسرعة"
                action_taken = "تايم آوت لمدة ساعة"
        SPAM_TRACKER[user_id] = (message.content, current_time)

    if violation_type:
        guild = message.guild
        admin_channel = discord.utils.get(guild.text_channels, name="admin-review")

        try:
            await message.delete()
        except:
            pass

        if "محجور" in action_taken:
            try:
                jail_role = discord.utils.get(guild.roles, name="محجور")
                if jail_role:
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

        if admin_channel:
            embed = discord.Embed(
                title="🚨 رصد مخالفة في الشات",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
            embed.add_field(name="العضو المخالف", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
            embed.add_field(name="الروم", value=message.channel.mention, inline=True)
            embed.add_field(name="نوع المخالفة", value=violation_type, inline=True)
            embed.add_field(name="الإجراء المتخذ", value=action_taken, inline=True)
            embed.add_field(name="محتوى الرسالة المحذوفة", value=message.content or "*(وسائط أو محتوى فارغ)*", inline=False)
            
            await admin_channel.send(embed=embed)
        return

    await bot.process_commands(message)


# ==================== نظام الترحيب وإرسال القوانين للخاص ====================

@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    
    # 1. إرسال القوانين للخاص بنفس شكل العنوان في الصورة + زر الانتقال للسيرفر
    try:
        # إنشاء رابط دعوة تلقائي لإضافته في الزر
        invite_url = None
        try:
            invites = await guild.invites()
            if invites:
                invite_url = invites[0].url
            elif guild.system_channel:
                new_invite = await guild.system_channel.create_invite(max_age=0, max_uses=0)
                invite_url = new_invite.url
            elif guild.text_channels:
                new_invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=0)
                invite_url = new_invite.url
        except Exception as e:
            print(f"⚠️ متعذر إنتاج رابط دعوة: {e}")

        dm_embed = discord.Embed(
            title=f"سيرفر {guild.name}⛅ |  - نرجو الالتزام |",
            description=RULES_TEXT,
            color=discord.Color.blurple()
        )

        view = View()
        if invite_url:
            view.add_item(Button(label=f"سيرفر {guild.name}", url=invite_url, style=discord.ButtonStyle.link))
            await member.send(embed=dm_embed, view=view)
        else:
            await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    # 2. الترحيب في روم الترحيب
    channel = discord.utils.get(guild.text_channels, name="الترحيب〢✋🏻")
    if channel:
        embed = discord.Embed(
            title="🎉 عضو جديد انضم إلينا!",
            description=f"مرحباً بك {member.mention} في 🌤️||\n**!{guild.name}**\n\nنتمنى لك قضاء وقت ممتع معنا.",
            color=discord.Color.brand_green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(content=member.mention, embed=embed)

    log_channel = discord.utils.get(guild.text_channels, name="دخول_خروج-💿") or discord.utils.get(guild.text_channels, name="دخول_خروج")
    if log_channel:
        log_embed = discord.Embed(title="📥 عضو جديد انضم للسيرفر", color=discord.Color.green(), timestamp=discord.utils.utcnow())
        log_embed.set_thumbnail(url=member.display_avatar.url)
        log_embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        log_embed.set_footer(text=f"عدد الأعضاء الآن: {guild.member_count}")
        await log_channel.send(embed=log_embed)

@bot.event
async def on_member_remove(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name="دخول_خروج-💿") or discord.utils.get(member.guild.text_channels, name="دخول_خروج")
    if channel:
        embed = discord.Embed(title="📤 عضو غادر السيرفر", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="العضو", value=f"{member.mention} (`{member.id}`)", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if before.roles != after.roles:
        channel = discord.utils.get(after.guild.text_channels, name="لوق_رتب-💿") or discord.utils.get(after.guild.text_channels, name="لوق_رتب")
        if channel:
            added_roles = [r for r in after.roles if r not in before.roles]
            removed_roles = [r for r in before.roles if r not in after.roles]
            
            embed = discord.Embed(title="👑 تحديث رتب عضو", color=discord.Color.blue(), timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=after.mention, inline=False)
            if added_roles:
                embed.add_field(name="🟢 رتب تمت إضافتها", value=", ".join([r.mention for r in added_roles]), inline=False)
            if removed_roles:
                embed.add_field(name="🔴 رتب تمت إزالتها", value=", ".join([r.mention for r in removed_roles]), inline=False)
            await channel.send(embed=embed)

    if before.nick != after.nick:
        channel = discord.utils.get(after.guild.text_channels, name="تغير_لقب-💿") or discord.utils.get(after.guild.text_channels, name="تغير_لقب")
        if channel:
            embed = discord.Embed(title="✏️ تغير لقب عضو", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
            embed.add_field(name="العضو", value=after.mention, inline=False)
            embed.add_field(name="اللقب القديم", value=before.nick or "لا يوجد", inline=True)
            embed.add_field(name="اللقب الجديد", value=after.nick or "لا يوجد", inline=True)
            await channel.send(embed=embed)

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    channel = discord.utils.get(message.guild.text_channels, name="لوق_الحذف-💿") or discord.utils.get(message.guild.text_channels, name="لوق_الحذف")
    if channel:
        embed = discord.Embed(title="🗑️ حذف رسالة", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
        embed.add_field(name="صاحب الرسالة", value=message.author.mention, inline=True)
        embed.add_field(name="الروم", value=message.channel.mention, inline=True)
        embed.add_field(name="محتوى الرسالة المحذوفة", value=message.content or "*(رسالة فارغة أو تحتوي على وسائط)*", inline=False)
        await channel.send(embed=embed)

@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    channel = discord.utils.get(guild.text_channels, name="لوق_طرد-💿") or discord.utils.get(guild.text_channels, name="لوق_طرد")
    if channel:
        embed = discord.Embed(title="🔨 حظر عضو (Ban)", color=discord.Color.dark_magenta(), timestamp=discord.utils.utcnow())
        embed.add_field(name="العضو المحظور", value=f"{user.mention} (`{user.id}`)", inline=False)
        await channel.send(embed=embed)


# ==================== الأجزاء التفاعلية والأزرار الدائمة ====================

class ApplicationModal(Modal, title="نموذج التقديم للإدارة"):
    q1 = TextInput(label="الاسم", placeholder="اكتب اسمك هنا...", required=True)
    q2 = TextInput(label="العمر", placeholder="اكتب عمرك...", required=True)
    q3 = TextInput(label="ما هو سبب دخولك للسيرفر؟", style=discord.TextStyle.paragraph, placeholder="اكتب سبب انضمامك...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        admin_channel = discord.utils.get(interaction.guild.text_channels, name="admin-review")
        if not admin_channel:
            await interaction.response.send_message("❌ لم يتم العثور على روم المراجعة `admin-review`.", ephemeral=True)
            return

        embed = discord.Embed(title="📥 طلب تقديم جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="المتقدم", value=interaction.user.mention, inline=False)
        embed.add_field(name="الاسم", value=self.q1.value, inline=False)
        embed.add_field(name="العمر", value=self.q2.value, inline=False)
        embed.add_field(name="سبب الدخول", value=self.q3.value, inline=False)

        view = AdminDecisionView(member=interaction.user)
        await admin_channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ تم إرسال تقديمك بنجاح إلى الإدارة!", ephemeral=True)

class ApplicationButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تقديم على الإدارة", style=discord.ButtonStyle.green, custom_id="apply_button_permanent_1")
    async def apply_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModal())

class AdminDecisionView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="قبول", style=discord.ButtonStyle.blurple, custom_id="accept_app_btn")
    async def accept_app(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        accepted_role = discord.utils.get(guild.roles, name="مسؤول-التقديم")
        if (accepted_role and accepted_role in interaction.user.roles) or is_exempted(interaction.user):
            try:
                await self.member.send("🎉 مبروك! تم قبول طلب تقديمك من الإدارة.")
            except:
                pass
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"✅ تم قبول طلب العضو {self.member.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ عذراً، الصلاحية غير متاحة لك.", ephemeral=True)

    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red, custom_id="reject_app_btn")
    async def reject_app(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        accepted_role = discord.utils.get(guild.roles, name="مسؤول-التقديم")
        if (accepted_role and accepted_role in interaction.user.roles) or is_exempted(interaction.user):
            try:
                await self.member.send("❌ نأسف لك، تم رفض طلب تقديمك من الإدارة.")
            except:
                pass
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"❌ تم رفض طلب العضو {self.member.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ عذراً، الصلاحية غير متاحة لك.", ephemeral=True)

class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn_permanent")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        ticket_role = discord.utils.get(guild.roles, name="مسؤول-التذاكر")
        if (ticket_role and ticket_role in interaction.user.roles) or is_exempted(interaction.user):
            await interaction.response.send_message("⏳ جاري إغلاق التذكرة وحذف الروم...", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ عذراً، لا تمتلك صلاحية إغلاق التذكرة.", ephemeral=True)

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة 🎫", style=discord.ButtonStyle.primary, custom_id="open_ticket_btn_permanent_1")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="التذاكر")
        if not category:
            category = await guild.create_category("التذاكر")

        channel_name = f"ticket-{interaction.user.name.lower()}"
        existing_channel = discord.utils.get(category.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(f"❌ لديك تذكرة مفتوحة بالفعل: {existing_channel.mention}", ephemeral=True)
            return

        ticket_role = discord.utils.get(guild.roles, name="مسؤول-التذاكر")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        if ticket_role:
            overwrites[ticket_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        
        embed = discord.Embed(title="تذكرة جديدة", description="أهلاً بك، يرجى كتابة مشكلتك أو استفسارك وسيقوم فريق الدعم بالرد عليك في أقرب وقت.", color=discord.Color.blue())
        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=CloseTicketButton())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك بنجاح: {ticket_channel.mention}", ephemeral=True)


# ==================== الأوامر الإدارية والأمان ====================

@bot.tree.command(name="حجر", description="حجر عضو يدوي وسحب رتبه وإعطاؤه رتبة محجور")
@discord.app_commands.describe(member="اختر العضو المراد حجره", reason="سبب الحجر")
async def jail_member(interaction: discord.Interaction, member: discord.Member, reason: str = "لم يتم تحديد سبب"):
    if not await check_owner_or_deputy_perm(interaction):
        return

    if is_exempted(member):
        await interaction.response.send_message("❌ لا يمكنك حجر هذا الشخص لأنه من الأشخاص أو الرتب المحمية!", ephemeral=True)
        return

    guild = interaction.guild
    jail_role = discord.utils.get(guild.roles, name="محجور")
    
    if not jail_role:
        await interaction.response.send_message("❌ لم يتم العثور على رتبة **محجور** بالسيرفر، يرجى التأكد من اسمها.", ephemeral=True)
        return

    try:
        saved_roles[member.id] = [r for r in member.roles if r != guild.default_role and r != jail_role]
        await member.edit(roles=[jail_role], reason=f"حجر يدوي بواسطة {interaction.user.name}: {reason}")
        
        admin_channel = discord.utils.get(guild.text_channels, name="admin-review")
        if admin_channel:
            embed = discord.Embed(title="🔒 تم حجر عضو", color=discord.Color.dark_red(), timestamp=discord.utils.utcnow())
            embed.add_field(name="المعاقب", value=member.mention, inline=False)
            embed.add_field(name="بواسطة", value=interaction.user.mention, inline=False)
            embed.add_field(name="السبب", value=reason, inline=False)
            await admin_channel.send(embed=embed)

        await interaction.response.send_message(f"✅ تم وضع العضو {member.mention} في الحجر وإعطاؤه رتبة **محجور** بنجاح.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ حدث خطأ أثناء تطبيق الحجر: {e}", ephemeral=True)


@bot.tree.command(name="فك_الحجر", description="إخراج عضو من الحجر وإعادة رتبه السابقة")
@discord.app_commands.describe(member="اختر العضو المراد إخراجه من الحجر")
async def unjail(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction):
        return

    jail_role = discord.utils.get(interaction.guild.roles, name="محجور")
    if jail_role and jail_role in member.roles:
        try:
            await member.remove_roles(jail_role)
        except:
            pass
    
    if member.id in saved_roles:
        roles_to_restore = [interaction.guild.get_role(r.id) for r in saved_roles[member.id] if interaction.guild.get_role(r.id)]
        try:
            await member.add_roles(*roles_to_restore)
        except:
            pass
        del saved_roles[member.id]
        
    await interaction.response.send_message(f"🔓 تم إخراج العضو {member.mention} من الحجر وإعادة رتبه السابقة بنجاح.", ephemeral=True)


@bot.tree.command(name="اعداد_اللوقات", description="إنشاء جميع رومات اللوقات الإدارية بدقة تلقائياً")
async def setup_logs(interaction: discord.Interaction):
    if not await check_owner_or_deputy_perm(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    category = discord.utils.get(guild.categories, name="سجلات الإدارة || 💿")
    if not category:
        category = await guild.create_category("سجلات الإدارة || 💿")

    log_names = [
        "لوق_تايم || 💿",
        "لوق_الحذف || 💿",
        "دخول_خروج || 💿",
        "لوق_طرد || 💿",
        "لوق_رتب || 💿",
        "تغير_لقب || 💿"
    ]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }

    created_count = 0
    for name in log_names:
        existing = discord.utils.get(category.text_channels, name=name)
        if not existing:
            await guild.create_text_channel(name, category=category, overwrites=overwrites)
            created_count += 1

    await interaction.followup.send(f"✅ تم إنشاء رومات اللوقات بنجاح داخل قسم `سجلات الإدارة || 💿` وعددها المستحدثة: {created_count}", ephemeral=True)


@bot.tree.command(name="اعداد_الرومات_الاساسيه", description="إعداد رومات النظام الأساسية والتذاكر والتقديم تلقائياً")
async def setup(interaction: discord.Interaction):
    if not await check_owner_or_deputy_perm(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    if not discord.utils.get(guild.roles, name="مسؤول-التذاكر"):
        await guild.create_role(name="مسؤول-التذاكر", color=discord.Color.blue())
    if not discord.utils.get(guild.roles, name="مسؤول-التقديم"):
        await guild.create_role(name="مسؤول-التقديم", color=discord.Color.purple())
    
    jail_role = discord.utils.get(guild.roles, name="محجور")

    jail_channel = discord.utils.get(guild.text_channels, name="quarantine-zone")
    if not jail_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }
        if jail_role:
            overwrites[jail_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        await guild.create_text_channel("quarantine-zone", overwrites=overwrites)
    else:
        if jail_role:
            await jail_channel.set_permissions(jail_role, view_channel=True, send_messages=True, read_message_history=True)
        await jail_channel.set_permissions(guild.default_role, view_channel=False)

    admin_channel = discord.utils.get(guild.text_channels, name="admin-review")
    if not admin_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        await guild.create_text_channel("admin-review", overwrites=overwrites)

    ticket_panel = discord.utils.get(guild.text_channels, name="الدعم-الفني🎫")
    if not ticket_panel:
        ticket_panel = await guild.create_text_channel("الدعم-الفني🎫")
    
    embed_ticket = discord.Embed(title="مركز الدعم والتذاكر", description="اضغط على الزر أدناه لفتح تذكرة خاصة للتواصل مع الإدارة.", color=discord.Color.green())
    await ticket_panel.send(embed=embed_ticket, view=TicketButtonView())

    apply_panel = discord.utils.get(guild.text_channels, name="التقديم-للسيرفر")
    if not apply_panel:
        apply_panel = await guild.create_text_channel("التقديم-للسيرفر")
        
    embed_apply = discord.Embed(title="التقديم لفريق الإدارة", description="اضغط على الزر أدناه لتعبئة استمارة التقديم.", color=discord.Color.purple())
    await apply_panel.send(embed=embed_apply, view=ApplicationButtonView())

    await interaction.followup.send("✅ تم إعداد رومات النظام والتذاكر والتقديم بنجاح!", ephemeral=True)


@bot.tree.command(name="روم_صوتي", description="تحديد روم صوتي دائم يدخله البوت تلقائياً ويعود إليه إذا خرج")
@discord.app_commands.describe(voice_channel="اختر الروم الصوتي من السيرفر")
async def voice_command(interaction: discord.Interaction, voice_channel: discord.VoiceChannel):
    if not await check_owner_or_deputy_perm(interaction):
        return

    await interaction.response.defer(ephemeral=True)
    try:
        global VOICE_CHANNEL_ID
        VOICE_CHANNEL_ID = voice_channel.id
        if interaction.guild.me.voice:
            await interaction.guild.me.voice.channel.disconnect()
        await voice_channel.connect()
        await interaction.followup.send(f"✅ تم ربط البوت بالروم الصوتي **{voice_channel.name}** ودخوله بنجاح!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء الاتصال بالروم: {e}", ephemeral=True)


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
                    if guild.me.voice:
                        try:
                            await guild.me.voice.channel.disconnect()
                        except:
                            pass
                    await channel.connect()
                except Exception as e:
                    print(f"فشل إعادة الاتصال بالروم الصوتي تلقائياً: {e}")


@bot.tree.command(name="تعيين_نائب", description="[لمالك البوت فقط] تعيين عضو كنائب للبوت")
@discord.app_commands.describe(member="اختر العضو المراد تعيينه كنائب")
async def setdeputy(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != BOT_OWNER_ID and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ عذراً، أمر تعيين النائب مخصص لمالك البوت فقط!", ephemeral=True)
        return

    global deputy_user_ids
    if member.id in deputy_user_ids:
        await interaction.response.send_message(f"⚠️ العضو {member.mention} موجود بالفعل ضمن قائمة النواب!", ephemeral=True)
        return

    deputy_user_ids.append(member.id)
    await interaction.response.send_message(f"✅ تم تعيين العضو {member.mention} كنائب جديد بنجاح!", ephemeral=True)


@bot.tree.command(name="إزالة_نائب", description="[لمالك البوت فقط] إزالة صفة النائب عن عضو معين")
@discord.app_commands.describe(member="اختر العضو المراد إزالة صفة النائب عنه")
async def removedeputy(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != BOT_OWNER_ID and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ عذراً، أمر إزالة النائب مخصص لمالك البوت فقط!", ephemeral=True)
        return

    global deputy_user_ids
    if member.id not in deputy_user_ids:
        await interaction.response.send_message(f"❌ العضو {member.mention} ليس موجوداً في قائمة النواب أساساً.", ephemeral=True)
        return

    deputy_user_ids.remove(member.id)
    await interaction.response.send_message(f"✅ تم بنجاح إزالة صفة النائب عن العضو {member.mention}.", ephemeral=True)


@bot.tree.command(name="حماية_شخص", description="إضافة شخص معين إلى قائمة المحميين فردياً")
@discord.app_commands.describe(member="اختر العضو المراد حمايته")
async def protect_person(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction):
        return

    global protected_users_list
    if member.id not in protected_users_list:
        protected_users_list.append(member.id)
        await interaction.response.send_message(f"🛡️ تمت إضافة العضو {member.mention} إلى قائمة الأشخاص المحميين بنجاح!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ العضو {member.mention} محمي مسبقاً.", ephemeral=True)


@bot.tree.command(name="إزالة_حماية_شخص", description="إزالة حماية شخص معين")
@discord.app_commands.describe(member="اختر العضو المراد إزالة الحماية عنه")
async def unprotect_person(interaction: discord.Interaction, member: discord.Member):
    if not await check_owner_or_deputy_perm(interaction):
        return

    global protected_users_list
    if member.id in protected_users_list:
        protected_users_list.remove(member.id)
        await interaction.response.send_message(f"🔓 تمت إزالة الحماية عن العضو {member.mention} بنجاح.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ العضو {member.mention} ليس موجوداً في قائمة الأشخاص المحميين أساساً.", ephemeral=True)


@bot.tree.command(name="حماية_رتبه", description="إضافة رتبه إلى قائمة الرتب المحمية")
@discord.app_commands.describe(role="اختر الرتبه المراد حمايتها")
async def protect_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_owner_or_deputy_perm(interaction):
        return

    global protected_roles_list
    if role.id not in protected_roles_list:
        protected_roles_list.append(role.id)
        await interaction.response.send_message(f"🛡️ تمت إضافة الرتبه {role.mention} إلى قائمة الرتب المحمية بنجاح!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ الرتبه {role.mention} محمية مسبقاً.", ephemeral=True)


@bot.tree.command(name="إزالة_حماية_رتبه", description="إزالة رتبه من قائمة الرتب المحمية")
@discord.app_commands.describe(role="اختر الرتبه المراد إزالة الحماية عنها")
async def unprotect_role(interaction: discord.Interaction, role: discord.Role):
    if not await check_owner_or_deputy_perm(interaction):
        return

    global protected_roles_list
    if role.id in protected_roles_list:
        protected_roles_list.remove(role.id)
        await interaction.response.send_message(f"🔓 تمت إزالة الحماية عن الرتبه {role.mention} بنجاح.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ الرتبه {role.mention} ليست موجودة في قائمة الرتب المحمية أساساً.", ephemeral=True)


@bot.tree.command(name="قائمة_الحماية", description="عرض لوحة شاملة لجميع الأشخاص والرتب والنواب المحميين")
async def protection_dashboard(interaction: discord.Interaction):
    global protected_users_list, protected_roles_list, deputy_user_ids

    embed = discord.Embed(
        title="🛡️ لوحة معلومات الحماية الشاملة",
        description="إليك تفاصيل الأشخاص والرتب والنواب المحميين في السيرفر حالياً:",
        color=discord.Color.gold()
    )

    users_text = "لا يوجد"
    if protected_users_list:
        valid_users = [f"• <@{uid}>" for uid in protected_users_list if interaction.guild.get_member(uid)]
        if valid_users:
            users_text = "\n".join(valid_users)
    embed.add_field(name=f"👤 الأشخاص المحميين ({len(protected_users_list)})", value=users_text, inline=False)

    roles_text = "لا توجد"
    if protected_roles_list:
        valid_roles = [f"• <@&{rid}>" for rid in protected_roles_list if interaction.guild.get_role(rid)]
        if valid_roles:
            roles_text = "\n".join(valid_roles)
    embed.add_field(name=f"👑 الرتب المحمية ({len(protected_roles_list)})", value=roles_text, inline=False)

    nawwab_text = "لا يوجد"
    if deputy_user_ids:
        valid_nawwab = [f"• <@{uid}>" for uid in deputy_user_ids if interaction.guild.get_member(uid)]
        if valid_nawwab:
            nawwab_text = "\n".join(valid_nawwab)
    embed.add_field(name=f"🛡️ النواب المعتمدون ({len(deputy_user_ids)})", value=nawwab_text, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="مسح", description="حذف عدد من الرسائل في الروم (الحد الأقصى 100 رسالة)")
@discord.app_commands.describe(amount="عدد الرسائل المراد حذفها (من 1 إلى 100)")
async def clear_messages(interaction: discord.Interaction, amount: int):
    if not await check_owner_or_deputy_perm(interaction):
        return

    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ عذراً، يجب أن يكون عدد الرسائل المراد حذفها بين **1 و 100** كحد أقصى.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ تم بنجاح حذف **{len(deleted)}** رسالة من هذا الروم.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ حدث خطأ أثناء محاولة حذف الرسائل: {e}", ephemeral=True)


@bot.tree.command(name="اعلان", description="نشر إعلان وتثبيته في روم الإعلانات تلقائياً")
@discord.app_commands.describe(text="اكتب نص الإعلان هنا")
async def announce(interaction: discord.Interaction, text: str):
    if not await check_owner_or_deputy_perm(interaction):
        return

    guild = interaction.guild
    announcement_channel = discord.utils.get(guild.text_channels, name="روم-الإعلانات")
    if not announcement_channel:
        announcement_channel = await guild.create_text_channel("روم-الإعلانات")

    embed = discord.Embed(title="📢 إعلان هام", description=text, color=discord.Color.gold())
    embed.set_footer(text=f"تم النشر بواسطة: {interaction.user.name}", icon_url=interaction.user.display_avatar.url)

    sent_message = await announcement_channel.send(embed=embed)
    try:
        await sent_message.pin()
    except:
        pass

    await interaction.response.send_message(f"✅ تم نشر الإعلان وتثبيته في روم {announcement_channel.mention} بنجاح!", ephemeral=True)


@bot.tree.command(name="قول", description="إرسال رسالة من خلال البوت إلى أي روم نصي تحدده")
@discord.app_commands.describe(channel="اختر الروم", message="اكتب الرسالة المراد إرسالها")
async def say_in_channel(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    if not await check_owner_or_deputy_perm(interaction):
        return

    await channel.send(message)
    await interaction.response.send_message(f"✅ تم إرسال رسالتك بنجاح إلى الروم {channel.mention}", ephemeral=True)


@bot.tree.command(name="خاص", description="إرسال رسالة خاصة (DM) لعضو معين من خلال البوت")
@discord.app_commands.describe(member="اختر العضو", message="اكتب الرسالة الخاصة")
async def send_dm(interaction: discord.Interaction, member: discord.Member, message: str):
    if not await check_owner_or_deputy_perm(interaction):
        return

    try:
        await member.send(f"📬 رسالة إدارية من سيرفر **{interaction.guild.name}**:\n\n{message}")
        await interaction.response.send_message(f"✅ تم إرسال الرسالة الخاصة إلى {member.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ لا يمكنني إرسال رسالة خاصة لهذا العضو (الخاص مقفل لديه).", ephemeral=True)


@bot.tree.command(name="المالك", description="عرض معلومات مالك البوت")
async def owner_info(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👑 معلومات مالك البوت",
        description="معلومات مالك ومصمم النظام:",
        color=discord.Color.purple()
    )
    embed.add_field(name="الاسم", value="Abo Shehri", inline=False)
    embed.add_field(name="حساب التواصل / المعرف", value="`ii.ih`", inline=False)
    await interaction.response.send_message(embed=embed)


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
                except Exception as e:
                    print(f"Failed to auto-connect to voice channel: {e}")

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
