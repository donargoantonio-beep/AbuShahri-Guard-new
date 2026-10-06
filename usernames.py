# ═══════════════════════════════════════════════════════════════
# 🔎 usernames.py -- ميزة اكتشاف اليوزرات (Groq AI)
# ═══════════════════════════════════════════════════════════════
"""
ميزة إضافية مستقلة:
- Groq AI لتوليد الأسماء
- فحص مباشر عبر HTTP (GitHub, Reddit)
- تعمل فقط في روم محدد
"""
import asyncio
import logging

import aiohttp
import discord
from discord import app_commands

import config

log = logging.getLogger("usernames")

SHARED: dict = {}


# ═══════════════════════════════════════════════════════════════
# 🎨 توليد الأسماء بالـ AI (Groq)
# ═══════════════════════════════════════════════════════════════

# قائمة الموديلات (نجرب واحد واحد حتى ينجح)
_GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "llama3-70b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


async def _call_groq(session, model_name, prompt):
    """طلب واحد لـ Groq بموديل معين"""
    headers = {
        "Authorization": "Bearer " + config.GROQ_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You output only usernames, one per line."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 1024,
    }

    async with session.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            return None, resp.status, text[:300]

        data = await resp.json()
        return data["choices"][0]["message"]["content"], 200, None


async def generate_usernames_with_ai(description: str,
                                      count: int = 10,
                                      max_length: int = 5) -> list:
    """يولّد أسماء مستخدمين قصيرة باستخدام Groq API"""
    if not config.GROQ_API_KEY:
        log.warning("GROQ_API_KEY غير موجود")
        return []

    prompt = (
        "Generate " + str(count) + " short English usernames, "
        + str(max_length) + " letters or fewer. "
        "Use REAL English words, all lowercase, no numbers, no symbols. "
        "Diverse (not all same theme). "
        "Theme: " + (description or "diverse, memorable words") + ". "
        "Return ONLY the usernames, one per line, nothing else."
    )

    text = None

    try:
        async with aiohttp.ClientSession() as session:
            for model_name in _GROQ_MODELS:
                try:
                    result, status, error = await _call_groq(session, model_name, prompt)

                    if status == 200 and result:
                        log.info("✅ نجح الموديل: %s", model_name)
                        text = result
                        break
                    else:
                        log.warning("فشل %s (status %d): %s",
                                    model_name, status, error)
                except Exception as e:
                    log.warning("خطأ في %s: %s", model_name, str(e)[:100])
                    continue

        if not text:
            log.error("كل الموديلات فشلت")
            return []

        names = []
        for line in text.split("\n"):
            name = line.strip().strip("-*\"'`.").strip()
            if name and name.isascii() and name.isalnum():
                if 2 <= len(name) <= max_length:
                    names.append(name.lower())

        return list(dict.fromkeys(names))[:count]

    except Exception as e:
        log.error("فشل توليد الأسماء: %s", e)
        return []


# ═══════════════════════════════════════════════════════════════
# 🔍 فحص التوفر عبر HTTP مباشر
# ═══════════════════════════════════════════════════════════════

async def _check_github(session, username):
    """فحص GitHub"""
    try:
        url = "https://api.github.com/users/" + username
        headers = {"User-Agent": "Discord-Bot"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return False
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


async def _check_reddit(session, username):
    """فحص Reddit"""
    try:
        url = "https://www.reddit.com/user/" + username + "/about.json"
        headers = {"User-Agent": "Discord-Bot/1.0"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("data", {}).get("name"):
                    return False
                return True
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


async def _check_pinterest(session, username):
    """فحص Pinterest"""
    try:
        url = "https://www.pinterest.com/" + username + "/"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10),
                                allow_redirects=True) as resp:
            if resp.status == 200:
                return False
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


async def check_usernames_availability(usernames: list,
                                        platforms: list) -> dict:
    """يفحص توفر الأسماء عبر المنصات"""
    results = {}

    async with aiohttp.ClientSession() as session:
        for username in usernames:
            results[username] = {"available": [], "taken": [], "unknown": []}

            for platform in platforms:
                result = None

                if platform == "GitHub":
                    result = await _check_github(session, username)
                elif platform == "Reddit":
                    result = await _check_reddit(session, username)
                elif platform == "Pinterest":
                    result = await _check_pinterest(session, username)
                else:
                    results[username]["unknown"].append(platform)
                    continue

                if result is True:
                    results[username]["available"].append(platform)
                elif result is False:
                    results[username]["taken"].append(platform)
                else:
                    results[username]["unknown"].append(platform)

                await asyncio.sleep(0.3)

    return results


# ═══════════════════════════════════════════════════════════════
# ⚙️ الأمر
# ═══════════════════════════════════════════════════════════════

def register_command(bot):
    """تسجيل أمر /اكتشف_يوزر"""

    @bot.tree.command(name="اكتشف_يوزر",
                      description="يولّد يوزرات قصيرة بالذكاء الاصطناعي ويفحص توفرها")
    @app_commands.describe(
        وصف="وصف اختياري",
        حرف="حرف محدد a-z",
        عدد="عدد الأسماء (1-20، افتراضي: 10)",
        طول="الحد الأقصى لطول الاسم (2-5، افتراضي: 5)",
    )
    async def discover_username_cmd(interaction: discord.Interaction,
                                     وصف: str = "",
                                     حرف: str = "",
                                     عدد: int = 10,
                                     طول: int = 5):

        if not getattr(config, "USERNAME_FINDER_ENABLED", True):
            await interaction.response.send_message(
                "هذه الميزة معطلة حالياً.", ephemeral=True
            )
            return

        allowed_channel_id = getattr(config, "USERNAME_FINDER_CHANNEL_ID", 0)
        if allowed_channel_id and interaction.channel_id != allowed_channel_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل فقط في <#" + str(allowed_channel_id) + ">.",
                ephemeral=True
            )
            return

        if عدد < 1 or عدد > 20:
            await interaction.response.send_message(
                "العدد يجب أن يكون بين 1 و 20.", ephemeral=True
            )
            return

        if طول < 2 or طول > 5:
            await interaction.response.send_message(
                "الطول يجب أن يكون بين 2 و 5.", ephemeral=True
            )
            return

        letter = حرف.strip().lower()
        if letter:
            if not (len(letter) == 1 and letter.isalpha() and letter.isascii()):
                await interaction.response.send_message(
                    "الحرف لازم a-z.", ephemeral=True
                )
                return
            وصف = "English words starting with the letter '" + letter + "'. " + وصف

        await interaction.response.defer(ephemeral=False)

        if not وصف.strip():
            وصف = "diverse short English words"

        candidates = await generate_usernames_with_ai(
            وصف, count=عدد, max_length=طول
        )

        if not candidates:
            await interaction.followup.send(
                "فشل توليد الأسماء. تأكد من `GROQ_API_KEY` في Render."
            )
            return

        platforms = getattr(config, "USERNAME_FINDER_PLATFORMS",
                            ["GitHub", "Reddit"])
        results = await check_usernames_availability(candidates, platforms)

        def score(n):
            return len(results.get(n, {}).get("available", []))

        sorted_names = sorted(results.keys(), key=score, reverse=True)

        total = len(platforms)
        fully_available = sum(
            1 for n in sorted_names if len(results[n]["available"]) == total
        )

        title = "🔎 نتائج فحص اليوزرات"
        if letter:
            title = "🔎 يوزرات تبدأ بحرف: " + letter.upper()

        desc_parts = []
        if letter:
            desc_parts.append("🔤 الحرف: `" + letter + "`")
        desc_parts.append("🎯 تم توليد: " + str(len(candidates)) + " أسماء")
        desc_parts.append("🌐 الفحص عبر: " + ", ".join(platforms))
        if fully_available:
            desc_parts.append("🎉 " + str(fully_available) + " متاحة على كل المنصات!")

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_parts),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow(),
        )

        for name in sorted_names[:20]:
            data = results[name]
            avail = data["available"]
            taken = data["taken"]

            if len(avail) == total:
                icon = "🌟"
            elif len(avail) >= 2:
                icon = "✅"
            elif len(avail) == 1:
                icon = "🔸"
            else:
                icon = "❌"

            platform_parts = []
            for p in platforms:
                if p in avail:
                    platform_parts.append("✅ " + p)
                elif p in taken:
                    platform_parts.append("❌ " + p)
                else:
                    platform_parts.append("❔ " + p)

            platform_line = " • ".join(platform_parts)

            if avail:
                summary = "**متاح على:** " + ", ".join(avail)
                if taken:
                    summary += "\n**محجوز على:** " + ", ".join(taken)
            else:
                summary = "**محجوز على كل المنصات**"

            embed.add_field(
                name=icon + " `" + name + "`",
                value=platform_line + "\n" + summary,
                inline=False,
            )

        embed.set_footer(text="💡 استخدم حرف: a ليوزرات تبدأ بحرف معين")

        await interaction.followup.send(embed=embed)

    log.info("✅ تم تسجيل أمر /اكتشف_يوزر")


def load_usernames(bot, shared: dict):
    """نقطة التحميل"""
    SHARED.clear()
    SHARED.update(shared)

    if not getattr(config, "USERNAME_FINDER_ENABLED", True):
        log.info("ميزة اليوزرات معطلة")
        return

    register_command(bot)
    log.info("✅ تم تحميل usernames.py")
