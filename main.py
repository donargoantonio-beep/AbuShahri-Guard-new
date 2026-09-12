import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import asyncio
import config

# إعداد سيرفر الـ Flask لضمان عمل البوت 24/7 عبر UptimeRobot
app = Flask('')

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run():
    app.run(host='0.0.0.0', port=5000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# إعدادات البوت والصلاحيات
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# دالة التحقق من صلاحيات المالك أو النائب
def is_owner_or_deputy():
    async def predicate(ctx):
        if ctx.author.id in config.OWNER_IDS:
            return True
        if config.OWNER_ROLE_ID and any(r.id == config.OWNER_ROLE_ID for r in ctx.author.roles):
            return True
        await ctx.send("❌ هذه الأوامر مخصصة للمالك أو النائب فقط!", delete_after=5)
        return False
    return commands.check(predicate)

# دالة عزل وضبط العضو في الحجر الصحي
async def quarantine_member(guild: discord.Guild, member: discord.Member, reason: str):
    q_role = discord.utils.get(guild.roles, name=config.QUARANTINE_ROLE_NAME)
    q_channel = discord.utils.get(guild.text_channels, name=config.QUARANTINE_CHANNEL_NAME)
    
    if not q_role or not q_channel:
        return

    # 1. سحب جميع رتب العضو (ما عدا @everyone والرتب الأساسية إن وجدت)
    roles_to_remove = [r for r in member.roles if r != guild.default_role and r != q_role]
    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove, reason=reason)
        except:
            pass

    # 2. إعطاؤه رتبة الحجر الصحي
    if q_role not in member.roles:
        try:
            await member.add_roles(q_role, reason=reason)
        except:
            pass

    # 3. إرسال تنبيه في روم الحجر
    await q_channel.send(f"🚨 تم حجر العضو {member.mention} | السبب: {reason}")

# نظام التذاكر
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label=config.TICKET_BUTTON_LABEL, style=discord.ButtonStyle.green, custom_id="open_ticket_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=config.TICKET_CATEGORY_NAME)
        support_role = discord.utils.get(guild.roles, name=config.SUPPORT_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        }
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(title="🎫 تذكرة جديدة", description=config.TICKET_WELCOME_MSG, color=discord.Color.blue())
        await ticket_channel.send(content=f"{interaction.user.mention} {support_role.mention if support_role else ''}", embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ تم فتح تذكرتك بنجاح: {ticket_channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="إغلاق التذكرة 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏳ سيتم حذف التذكرة خلال 5 ثوانٍ...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# نظام التقديم
class ApplyModal(discord.ui.Modal, title=config.APPLY_MODAL_TITLE):
    ans1 = discord.ui.TextInput(label=config.QUESTION_1, style=discord.TextStyle.short)
    ans2 = discord.ui.TextInput(label=config.QUESTION_2, style=discord.TextStyle.short)
    ans3 = discord.ui.TextInput(label=config.QUESTION_3, style=discord.TextStyle.long)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        review_channel = discord.utils.get(guild.text_channels, name=config.ADMIN_REVIEW_CHANNEL_NAME)
        
        embed = discord.Embed(title="📝 طلب تقديم جديد", color=discord.Color.gold())
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name=config.QUESTION_1, value=self.ans1.value, inline=False)
        embed.add_field(name=config.QUESTION_2, value=self.ans2.value, inline=False)
        embed.add_field(name=config.QUESTION_3, value=self.ans3.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        if review_channel:
            await review_channel.send(embed=embed, view=ReviewApplyView(interaction.user.id))
        
        await interaction.response.send_message("✅ تم إرسال تقديمك بنجاح، سيتم مراجعته قريباً!", ephemeral=True)

class ReviewApplyView(discord.ui.View):
    def __init__(self, applicant_id):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id

    @discord.ui.button(label="قبول ✅", style=discord.ButtonStyle.green, custom_id="accept_apply")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        role = discord.utils.get(guild.roles, name=config.SUPPORT_ROLE_NAME)
        
        if member and role:
            await member.add_roles(role)
            try:
                await member.send("🎉 مبروك! تم قبول تقديمك والانضمام لفريق العمل.")
            except:
                pass
        await interaction.message.edit(content=f"✅ تم القبول بواسطة {interaction.user.mention}", view=None)

    @discord.ui.button(label="رفض ❌", style=discord.ButtonStyle.red, custom_id="reject_apply")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.applicant_id)
        if member:
            try:
                await member.send("❌ نأسف، تم رفض تقديمك في الوقت الحالي.")
            except:
                pass
        await interaction.message.edit(content=f"❌ تم الرفض بواسطة {interaction.user.mention}", view=None)

class ApplyButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="قدم هنا 📋", style=discord.ButtonStyle.blurple, custom_id="apply_btn")
    async def apply_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplyModal())

# عند تشغيل البوت: بناء الرتب، الرومات، وتعديل صلاحيات رؤية القنوات
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    for guild in bot.guilds:
        # 1. إنشاء رتبة الدعم
        support_role = discord.utils.get(guild.roles, name=config.SUPPORT_ROLE_NAME)
        if not support_role:
            await guild.create_role(name=config.SUPPORT_ROLE_NAME, color=discord.Color.green())

        # 2. إنشاء رتبة الحجر الصحي
        q_role = discord.utils.get(guild.roles, name=config.QUARANTINE_ROLE_NAME)
        if not q_role:
            # رتبة لونها رمادي بدون صلاحيات
            q_role = await guild.create_role(name=config.QUARANTINE_ROLE_NAME, color=discord.Color.dark_embed(), permissions=discord.Permissions.none())

        # 3. إنشاء روم الحجر الصحي وضبط صلاحياته بحيث لا يرى ولا يكتب إلا فيه فقط
        q_channel = discord.utils.get(guild.text_channels, name=config.QUARANTINE_CHANNEL_NAME)
        if not q_channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                q_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }
            q_channel = await guild.create_text_channel(name=config.QUARANTINE_CHANNEL_NAME, overwrites=overwrites)
        else:
            # تأكد أن صلاحية الروم تحجب الجميع وتسمح لرتبة الحجر فقط
            await q_channel.set_permissions(guild.default_role, view_channel=False)
            await q_channel.set_permissions(q_role, view_channel=True, send_messages=True)

        # 4. منع رتبة الحجر من رؤية باقي الرومات في السيرفر تلقائياً
        for channel in guild.channels:
            if channel.name != config.QUARANTINE_CHANNEL_NAME:
                try:
                    await channel.set_permissions(q_role, view_channel=False)
                except:
                    pass

        # 5. إنشاء كاتيجوري التذاكر وروم الإدارة
        category = discord.utils.get(guild.categories, name=config.TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(config.TICKET_CATEGORY_NAME)

        review_channel = discord.utils.get(guild.text_channels, name=config.ADMIN_REVIEW_CHANNEL_NAME)
        if not review_channel:
            await guild.create_text_channel(name=config.ADMIN_REVIEW_CHANNEL_NAME, category=category)

    print("Setup completed successfully!")

# نظام الحماية: مراقبة محاولة سحب الرتب المحمية
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    removed_roles = [r for r in before.roles if r not in after.roles]
    for role in removed_roles:
        if role.id in config.PROTECTED_ROLE_IDS:
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                actor = entry.user
                if actor.id == bot.user.id or actor.id in config.OWNER_IDS:
                    return
                
                # عزل المخرب فوراً للحجر الصحي وسحب رتبه
                await quarantine_member(after.guild, actor, f"محاولة سحب رتبة محمية: {role.name}")
                return

# أمر يدوي لحجر أي شخص (`!quarantine @user`)
@bot.command()
@is_owner_or_deputy()
async def quarantine(ctx, member: discord.Member, *, reason="مخالفة قوانين السيرفر"):
    await quarantine_member(ctx.guild, member, reason)
    await ctx.send(f"✅ تم حجر العضو {member.mention} بنجاح.", delete_after=5)
    await ctx.message.delete()

# أمر لإرسال لوحات التذاكر والتقديم
@bot.command()
@is_owner_or_deputy()
async def setup(ctx):
    ticket_embed = discord.Embed(title=config.TICKET_PANEL_TITLE, description=config.TICKET_PANEL_DESC, color=discord.Color.green())
    await ctx.send(embed=ticket_embed, view=TicketView())

    apply_embed = discord.Embed(title="📝 التقديم على الإدارة", description="اضغط على الزر أدناه لفتح استمارة التقديم.", color=discord.Color.blurple())
    await ctx.send(embed=apply_embed, view=ApplyButtonView())
    
    await ctx.message.delete()

# تشغيل السيرفر والبوت
keep_alive()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
