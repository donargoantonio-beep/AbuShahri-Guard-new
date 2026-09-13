# main.py
import discord
from discord.ext import commands
import os
from keep_alive import keep_alive
import config

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Bot is ready and online!")

# أمر الـ setup بدون قيود أيدي حالياً للتجربة والتأكد من الاستجابة
@bot.command(name="setup")
async def setup_bot(ctx):
    guild = ctx.guild
    
    # 1. إنشاء رتبة محجور إذا لم تكن موجودة
    quarantine_role = discord.utils.get(guild.roles, name=config.QUARANTINE_ROLE_NAME)
    if not quarantine_role:
        quarantine_role = await guild.create_role(name=config.QUARANTINE_ROLE_NAME, color=discord.Color.red())
    
    # 2. إنشاء روم الحجر الصحي
    quarantine_channel = discord.utils.get(guild.text_channels, name=config.QUARANTINE_CHANNEL_NAME)
    if not quarantine_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            quarantine_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        quarantine_channel = await guild.create_text_channel(config.QUARANTINE_CHANNEL_NAME, overwrites=overwrites)
    
    # 3. إنشاء كاتيجوري التذاكر والروم الخاص بالمراجعة واللوحة
    category = discord.utils.get(guild.categories, name=config.TICKET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(config.TICKET_CATEGORY_NAME)
        
    admin_review = discord.utils.get(guild.text_channels, name=config.ADMIN_REVIEW_CHANNEL_NAME)
    if not admin_review:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        admin_review = await guild.create_text_channel(config.ADMIN_REVIEW_CHANNEL_NAME, category=category, overwrites=overwrites)

    # إرسال رسالة نجاح في الشات
    await ctx.send("✅ تم تنفيذ أمر الـ Setup بنجاح وتم إنشاء الرومات والرتب المطلوبة!")

# تشغيل سيرفر الويب للحفاظ على البوت شغال (Keep-Alive)
keep_alive()

# تشغيل البوت بالتوكن المخزن في متغيرات البيئة
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN is not found in environment variables!")
