# ═══════════════════════════════════════════════════════════════
# 🔎 usernames.py -- ميزة اكتشاف اليوزرات (Groq AI)
# ═══════════════════════════════════════════════════════════════
"""
ميزة إضافية مستقلة:
- Groq AI لتوليد الأسماء
- فحص مباشر عبر HTTP (GitHub, Reddit, Instagram, TikTok, Snapchat, Telegram)
- تعرض المتاح فقط
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

_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
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
# 🔍 فحص التوفر عبر منصات متعددة
# ═══════════════════════════════════════════════════════════════

async def _check_github(session, username):
    """فحص GitHub — يرجع True (متاح) / False (محجوز) / None (خطأ)"""
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
        headers = {"User-Agent": "Mozilla/5.0 DiscordBot/1.0"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json()
                except Exception:
                    return None
                # لو فيه error -> متاح
                if "error" in data or data.get("error"):
                    return True
                # لو فيه اسم -> محجوز
                if data.get("data", {}).get("name"):
                    return False
                return True
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


async def _check_instagram(session, username):
    """فحص Instagram"""
    try:
        url = "https://www.instagram.com/" + username + "/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10),
                                allow_redirects=False) as resp:
            if resp.status == 404:
                return True
            elif resp.status == 200:
                return False
            elif resp.status in (301, 302):
                # إعادة توجيه لصفحة الدخول = غير موجود
                return True
            return None
    except Exception:
        return None


async def _check_tiktok(session, username):
    """فحص TikTok"""
    try:
        url = "https://www.tiktok.com/@" + username
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10),
                                allow_redirects=True) as resp:
            if resp.status == 404:
                return True
            elif resp.status == 200:
                try:
                    text = await resp.text()
                except Exception:
                    return None
                # لو فيه رسائل "غير موجود"
                not_found_markers = [
                    "Couldn't find this account",
                    "Couldn't find this user",
                    "تعذر العثور على هذا الحساب",
                    "找不到此帐号",
                ]
                for marker in not_found_markers:
                    if marker in text:
                        return True
                return False
            return None
    except Exception:
        return None


async def _check_snapchat(session, username):
    """فحص Snapchat"""
    try:
        url = "https://www.snapchat.com/add/" + username
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10),
                                allow_redirects=True) as resp:
            if resp.status == 404:
                return True
            elif resp.status == 200:
                try:
                    text = await resp.text()
                except Exception:
                    return None
                not_found_markers = [
                    "This Snapcode doesn't exist",
                    "Sorry, we couldn't find",
                ]
                for marker in not_found_markers:
                    if marker in text:
                        return True
                return False
            return None
    except Exception:
        return None


async def _check_telegram(session, username):
    """فحص Telegram"""
    try:
        url = "https://t.me/" + username
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10),
                                allow_redirects=True) as resp:
            if resp.status == 200:
                try:
                    text = await resp.text()
                except Exception:
                    return None
                # لو فيه "tgme_page_title" -> موجود
                if "tgme_page_title" in text:
                    return False
                # لو فيه رسالة "username not found"
                if "If you have Telegram" not in text and "tgme_page" not in text:
                    return True
                return None
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


# ─── خريطة المنصات ───
_PLATFORM_CHECKERS = {
    "GitHub": _check_github,
    "Reddit": _check_reddit,
    "Instagram": _check_instagram,
    "TikTok": _check_tiktok,
    "Snapchat": _check_snapchat,
    "Telegram": _check_telegram,
    "Pinterest": _check_pinterest,
}


async def check_usernames_availability(usernames: list,
                                        platforms: list) -> dict:
    """يفحص توفر الأسماء عبر المنصات"""
    results = {}

    async with aiohttp.ClientSession() as session:
        for username in usernames:
            results[username] = {"available": [], "taken": [], "unknown": []}

            for platform in platforms:
                checker = _PLATFORM_CHECKERS.get(platform)
                if not checker:
                    results[username]["unknown"].append(platform)
                    continue

                try:
                    result = await checker(session, username)
                except Exception as e:
                    log.warning("خطأ في %s لـ %s: %s", platform, username, str(e)[:100])
                    result = None

                if result is True:
                    results[username]["available"].append(platform)
                elif result is False:
                    results[username]["taken"].append(platform)
                else:
                    results[username]["unknown"].append(platform)

                await asyncio.sleep(0.2)

    return results


# ═══════════════════════════════════════════════════════════════
# 🔄 توليد المتاح فقط (يستبدل المحجوز)
# ═══════════════════════════════════════════════════════════════

async def generate_available_usernames(description: str,
                                        count: int,
                                        max_length: int,
                                        platforms: list,
                                        max_rounds: int = 3):
    """
    يولّد أسماء ويستبدل المحجوز تلقائياً حتى يصل للعدد المطلوب
    يرجع قائمة (name, data) للمتاحين فقط
    """
    available = []
    seen = set()

    for round_num in range(max_rounds):
        needed = count - len(available)
        if needed <= 0:
            break

        # نطلب أكثر (× 3) عشان نضمن الوصول للعدد
        request_count = min(needed * 3, 20)

        log.info("الجولة %d: نولّد %d اسم عشان نكمل %d",
                 round_num + 1, request_count, needed)

        candidates = await generate_usernames_with_ai(
            description, count=request_count, max_length=max_length
        )

        # احذف المكرر
        candidates = [c for c in candidates if c not in seen]
        seen.update(candidates)

        if not candidates:
            log.warning("AI ما رجّع أسماء في الجولة %d", round_num + 1)
            break

        results = await check_usernames_availability(candidates, platforms)

        # خذ المتاح فقط
        for name, data in results.items():
            # نتجاهل اللي عنده أي منصة "محجوز"
            if data["taken"]:
                continue

            # لازم يكون متاح على منصة واحدة على الأقل (مو كلها unknown)
            if not data["available"]:
                continue

            if len(available) < count:
                available.append((name, data))

    return available


# ═══════════════════════════════════════════════════════════════
# ⚙️ الأمر
# ═══════════════════════════════════════════════════════════════

def register_command(bot):
    """تسجيل أمر /اكتشف_يوزر"""

    @bot.tree.command(name="اكتشف_يوزر",
                      description="يولّد يوزرات قصيرة متاحة (يستبدل المحجوز تلقائياً)")
    @app_commands.describe(
        وصف="وصف اختياري",
        حرف="حرف محدد a-z",
        عدد="عدد الأسماء المتاحة المطلوبة (1-20، افتراضي: 5)",
        طول="الحد الأقصى لطول الاسم (2-5، افتراضي: 5)",
    )
    async def discover_username_cmd(interaction: discord.Interaction,
                                     وصف: str = "",
                                     حرف: str = "",
                                     عدد: int = 5,
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

        platforms = getattr(config, "USERNAME_FINDER_PLATFORMS",
                            ["GitHub", "Reddit", "Instagram", "TikTok", "Snapchat", "Telegram"])

        # ⭐ توليد المتاح فقط
        available = await generate_available_usernames(
            وصف, count=عدد, max_length=طول, platforms=platforms
        )

        if not available:
            await interaction.followup.send(
                "ما قدرت ألقى أسماء متاحة. جرّب مرة ثانية أو وصف مختلف."
            )
            return

        title = "🔎 يوزرات متاحة"
        if letter:
            title = "🔎 يوزرات متاحة تبدأ بحرف: " + letter.upper()

        total = len(platforms)
        desc_parts = [
            "🎯 **عدد المتاح:** " + str(len(available)),
            "🌐 **الفحص عبر:** " + ", ".join(platforms),
        ]
        if letter:
            desc_parts.insert(0, "🔤 **الحرف:** `" + letter + "`")

        embed = discord.Embed(
            title=title,
            description="\n".join(desc_parts),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        for name, data in available[:20]:
            avail = data["available"]
            unknown = data["unknown"]

            if len(avail) == total:
                icon = "🌟"
            elif len(avail) >= 3:
                icon = "✅"
            else:
                icon = "🔸"

            # ✅ كل منصة
            platform_parts = []
            for p in platforms:
                if p in avail:
                    platform_parts.append("✅ " + p)
                elif p in unknown:
                    platform_parts.append("❔ " + p)
                else:
                    platform_parts.append("⏭️ " + p)  # تم تخطيها

            platform_line = " • ".join(platform_parts)

            # التفاصيل
            if len(avail) == total:
                summary = "🎉 **متاح على كل المنصات**"
            else:
                summary = "**متاح على:** " + ", ".join(avail)
                if unknown:
                    summary += "\n**غير معروف:** " + ", ".join(unknown)

            embed.add_field(
                name=icon + " `" + name + "`",
                value=platform_line + "\n" + summary,
                inline=False,
            )

        embed.set_footer(text="💡 كل الأسماء المعروضة متاحة على الأقل في منصة واحدة")

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
