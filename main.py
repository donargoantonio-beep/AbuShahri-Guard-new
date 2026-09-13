import os
import asyncio
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

saved_roles = {}
protected_roles_list = []
deputy_role_id = None

# دالة التحقق: المالك أو النائب المعين فقط
def check_owner_or_deputy(interaction: discord.Interaction):
    if interaction.user.id == interaction.guild.owner_id:
        return True
    if deputy_role_id and any(r.id == deputy_role_id for r in interaction.user.roles):
        return True
    return False

# ==================== 1. نظام الحماية (Anti-Nuke) ====================
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if len(before.roles) > len(after.roles):
        removed_roles = set(before.roles) - set(after.roles)
        for role in removed_roles:
            if role.id in protected_roles_list:
                guild = after.guild
                jail_channel = discord.utils.get(guild.text_channels, name="quarantine-zone")
                
                saved_roles[after.id] = [r for r in after.roles if r != guild.default_role]
                
                try:
                    await after.edit(roles=[])
                except:
                    pass
                
                if jail_channel:
                    await jail_channel.set_permissions(after, view_channel=True, send_messages=False)
                    
                admin_review = discord.utils.get(guild.text_channels, name="admin-review")
                if admin_review:
                    await admin_review.send(f"🚨 **تنبيه أمني:** حاول العضو {after.mention} التلاعب برتبة محمية (`{role.name}`). تم نقله إلى `quarantine-zone` وسحب جميع رتبه!")
                break

# ==================== 2. نظام التقديم ====================
class ApplicationModal(Modal, title="نموذج التقديم للإدارة"):
    q1 = TextInput(label="الاسم", placeholder="اكتب اسمك هنا...", required=True)
    q2 = TextInput(label="العمر", placeholder="اكتب عمرك...", required=True)
    q3 = TextInput(label="ايش سبب دخولك السيرفر", style=discord.TextStyle.paragraph, placeholder="اكتب سبب دخولك...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        admin_channel = discord.utils.get(interaction.guild.text_channels, name="admin-review")
        if not admin_channel:
            await interaction.response.send_message("❌ لم يتم العثور على روم المراجعة للإدارة `admin-review`.", ephemeral=True)
            return

        embed = discord.Embed(title="📥 طلب تقديم جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="المتقدم", value=interaction.user.mention, inline=False)
        embed.add_field(name="الاسم", value=self.q1.value, inline=False)
        embed.add_field(name="العمر", value=self.q2.value, inline=False)
        embed.add_field(name="سبب دخول السيرفر", value=self.q3.value, inline=False)

        view = AdminDecisionView(member=interaction.user)
        await admin_channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ تم إرسال تقديمك بنجاح إلى الإدارة!", ephemeral=True)

class ApplicationButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تقديم على الإدارة", style=discord.ButtonStyle.green, custom_id="apply_button")
    async def apply_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModal())

class AdminDecisionView(View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="قبول", style=discord.ButtonStyle.blurple, custom_id="accept_app")
    async def accept_app(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        accepted_role = discord.utils.get(guild.roles, name="مسؤول-التقديم")
        if (accepted_role and accepted_role in interaction.user.roles) or check_owner_or_deputy(interaction):
            try:
                await self.member.send("🎉 مبروك! تم **قبول** طلب تقديمك للإدارة.")
            except:
                pass
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"✅ تم قبول طلب العضو {self.member.mention} بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ليس لديك صلاحية قبول التقديم!", ephemeral=True)

    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red, custom_id="reject_app")
    async def reject_app(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        accepted_role = discord.utils.get(guild.roles, name="مسؤول-التقديم")
        if (accepted_role and accepted_role in interaction.user.roles) or check_owner_or_deputy(interaction):
            try:
                await self.member.send("❌ نأسف لك، تم **رفض** طلب تقديمك للإدارة في الوقت الحالي.")
            except:
                pass
            await interaction.message.edit(view=None)
            await interaction.response.send_message(f"❌ تم رفض طلب العضو {self.member.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ليس لديك صلاحية رفض التقديم!", ephemeral=True)


# ==================== 3. نظام التذاكر ====================
class CloseTicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        ticket_role = discord.utils.get(guild.roles, name="مسؤول-التذاكر")
        if (ticket_role and ticket_role in interaction.user.roles) or check_owner_or_deputy(interaction):
            await interaction.response.send_message("⏳ جاري إغلاق التذكرة وحذف الروم...", ephemeral=True)
            await asyncio.sleep(2)
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ لا تملك صلاحية إغلاق التذكرة!", ephemeral=True)

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="فتح تذكرة 🎫", style=discord.ButtonStyle.primary, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="التذاكر")
        if not category:
            category = await guild.create_category("التذاكر")

        channel_name = f"ticket-{interaction.user.name}"
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
        
        embed = discord.Embed(title="تذكرة جديدة", description="أهلاً بك، يرجى كتابة مشكلتك أو استفسارك وسيقوم فريق الدعم بالرد عليك قريباً.", color=discord.Color.blue())
        await ticket_channel.send(content=f"{interaction.user.mention}", embed=embed, view=CloseTicketButton())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك بنجاح: {ticket_channel.mention}", ephemeral=True)


# ==================== 4. أوامر الـ Slash Commands ====================

@bot.tree.command(name="setup", description="إعداد الرومات والتذاكر والتقديم وتحديد الروم الصوتي للبوت")
@discord.app_commands.describe(
    voice_channel="اختر الروم الصوتي الموجود أساساً عندك ليدخل فيه البوت 24 ساعة",
    deputy_role="اختر رتبة النائب"
)
async def setup(interaction: discord.Interaction, voice_channel: discord.VoiceChannel, deputy_role: discord.Role = None):
    if not check_owner_or_deputy(interaction):
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب السيرفر أو النائب فقط!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    global deputy_role_id
    if deputy_role:
        deputy_role_id = deputy_role.id

    if not discord.utils.get(guild.roles, name="مسؤول-التذاكر"):
        await guild.create_role(name="مسؤول-التذاكر", color=discord.Color.blue())
    if not discord.utils.get(guild.roles, name="مسؤول-التقديم"):
        await guild.create_role(name="مسؤول-التقديم", color=discord.Color.purple())

    jail_channel = discord.utils.get(guild.text_channels, name="quarantine-zone")
    if not jail_channel:
        overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=False, speak=False)}
        await guild.create_text_channel("quarantine-zone", overwrites=overwrites)

    admin_channel = discord.utils.get(guild.text_channels, name="admin-review")
    if not admin_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }
        await guild.create_text_channel("admin-review", overwrites=overwrites)

    try:
        if interaction.guild.me.voice:
            await interaction.guild.me.voice.channel.disconnect()
        await voice_channel.connect()
    except Exception as e:
        print(f"Could not connect to voice channel: {e}")

    ticket_panel = discord.utils.get(guild.text_channels, name="روم-التذاكر")
    if not ticket_panel:
        ticket_panel = await guild.create_text_channel("روم-التذاكر")
    
    embed_ticket = discord.Embed(title="مركز الدعم والتذاكر", description="اضغط على الزر أدناه لفتح تذكرة خاصة للتواصل مع الإدارة.", color=discord.Color.green())
    await ticket_panel.send(embed=embed_ticket, view=TicketButtonView())

    apply_panel = discord.utils.get(guild.text_channels, name="تقديم-الإدارة")
    if not apply_panel:
        apply_panel = await guild.create_text_channel("تقديم-الإدارة")
        
    embed_apply = discord.Embed(title="التقديم لفريق الإدارة", description="اضغط على الزر أدناه لتعبئة استبيان التقديم.", color=discord.Color.purple())
    await apply_panel.send(embed=embed_apply, view=ApplicationButtonView())

    await interaction.followup.send(f"✅ تم الإعداد بنجاح! والبوت متواجد الآن في الروم الصوتي: **{voice_channel.name}**", ephemeral=True)


@bot.tree.command(name="setrole", description="تعيين رتبة النائب للتحكم بالبوت")
@discord.app_commands.describe(role="اختر رتبة النائب")
async def setrole(interaction: discord.Interaction, role: discord.Role):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ هذا الأمر خاص بصاحب السيرفر الأساسي فقط!", ephemeral=True)
        return

    global deputy_role_id
    deputy_role_id = role.id
    await interaction.response.send_message(f"✅ تم تعيين رتبة **{role.name}** كـ نائب صاحب البوت بنجاح!", ephemeral=True)


@bot.tree.command(name="protect", description="حماية رتبة معينة من التخريب أو السحب")
@discord.app_commands.describe(role="اختر الرتبة المراد حمايتها")
async def protect(interaction: discord.Interaction, role: discord.Role):
    if not check_owner_or_deputy(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الأمر!", ephemeral=True)
        return

    if role.id not in protected_roles_list:
        protected_roles_list.append(role.id)
        await interaction.response.send_message(f"🛡️ تمت إضافة رتبة **{role.name}** إلى قائمة الرتب المحمية ضد العبث والسحب!", ephemeral=True)
    else:
        await interaction.response.send_message(f"⚠️ الرتبة **{role.name}** محمية مسبقاً.", ephemeral=True)


@bot.tree.command(name="unjail", description="إخراج عضو من الحجر وإرجاع رتبه السابقة")
@discord.app_commands.describe(member="اختر العضو المراد إخراجه من الحجر")
async def unjail(interaction: discord.Interaction, member: discord.Member):
    if not check_owner_or_deputy(interaction):
        await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الأمر!", ephemeral=True)
        return

    jail_channel = discord.utils.get(interaction.guild.text_channels, name="quarantine-zone")
    if jail_channel:
        await jail_channel.set_permissions(member, overwrite=None)
    
    if member.id in saved_roles:
        roles_to_restore = [interaction.guild.get_role(r.id) for r in saved_roles[member.id] if interaction.guild.get_role(r.id)]
        try:
            await member.add_roles(*roles_to_restore)
        except:
            pass
        del saved_roles[member.id]
        
    await interaction.response.send_message(f"🔓 تم إخراج العضو {member.mention} من الحجر وإرجاع رتبه السابقة بنجاح.", ephemeral=True)


@bot.tree.command(name="اعلان", description="إنشاء روم إعلانات ونشر إعلان وتثبيته تلقائياً")
@discord.app_commands.describe(text="اكتب نص الإعلان هنا")
async def announce(interaction: discord.Interaction, text: str):
    if not check_owner_or_deputy(interaction):
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب السيرفر أو النائب فقط!", ephemeral=True)
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
    if not check_owner_or_deputy(interaction):
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب السيرفر أو النائب فقط!", ephemeral=True)
        return

    await channel.send(message)
    await interaction.response.send_message(f"✅ تم إرسال رسالتك بنجاح إلى الروم {channel.mention}", ephemeral=True)


@bot.tree.command(name="خاص", description="إرسال رسالة خاصة (DM) لعضو معين من خلال البوت")
@discord.app_commands.describe(member="اختر العضو", message="اكتب الرسالة الخاصة")
async def send_dm(interaction: discord.Interaction, member: discord.Member, message: str):
    if not check_owner_or_deputy(interaction):
        await interaction.response.send_message("❌ هذا الأمر مخصص لصاحب السيرفر أو النائب فقط!", ephemeral=True)
        return

    try:
        await member.send(f"📬 رسالة إدارية من سيرفر **{interaction.guild.name}**:\n\n{message}")
        await interaction.response.send_message(f"✅ تم إرسال الرسالة الخاصة إلى {member.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ لا يمكنني إرسال رسالة خاصة لـ {member.mention} (الخاص مقفل عنده أو حظر البوت).", ephemeral=True)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Bot is ready, all slash commands synced successfully!")

keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
