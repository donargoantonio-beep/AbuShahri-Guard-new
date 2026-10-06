# ═══════════════════════════════════════════════════════════════
# 🔎 usernames.py -- إصدار 3.0
# ═══════════════════════════════════════════════════════════════
"""
ميزة إضافية مستقلة:
- Groq AI لتوليد الأسماء
- فحص مباشر عبر HTTP (Reddit, Instagram, TikTok, Snapchat, Telegram)
- 15 يوزر متاح في كل طلب
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
# 🎨 توليد الأسماء بالـ AI
# ═══════════════════════════════════════════════════════════════

_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.6-27b",
]


async def _call_groq(session, model_name, prompt):
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
        "temperature": 0.95,
        "max_tokens": 2048,
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
                                      count: int = 20,
                                      max_length: int = 5) -> list:
    """يولّد أسماء مستخدمين قصيرة باستخدام Groq API"""
    if not config.GROQ_API_KEY:
        return []

    prompt = (
        "Generate " + str(count) + " short English usernames, "
        + str(max_length) + " letters or fewer. "
        "Use REAL English words (nouns, verbs, adjectives), all lowercase, "
        "no numbers, no symbols, no spaces. "
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
                        log.warning("فشل %s (status %d)", model_name, status)
                except Exception as e:
                    log.warning("خطأ في %s: %s", model_name, str(e)[:100])
                    continue

        if not text:
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
# 🔍 فحوصات المنصات
# ═══════════════════════════════════════════════════════════════

async def _check_reddit(session, username):
    """Reddit — دقيق"""
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
                if data.get("error") == 404:
                    return True
                if data.get("data", {}).get("name"):
                    return False
                return True
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


async def _check_instagram(session, username):
    """Instagram — باستخدام API الداخلي"""
    try:
        url = ("https://www.instagram.com/api/v1/users/web_profile_info/"
               "?username=" + username)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-IG-App-ID": "936619743392459",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 404:
                return True
            if resp.status == 200:
                try:
                    data = await resp.json()
                except Exception:
                    return None
                user = data.get("data", {}).get("user")
                if user is None:
                    return True
                if user.get("username"):
                    return False
            return None
    except Exception:
        return None


async def _check_tiktok(session, username):
    """TikTok — باستخدام API الداخلي"""
    try:
        url = "https://www.tiktok.com/api/user/detail/?uniqueId=" + username
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json()
                except Exception:
                    return None
                if not data.get("userInfo"):
                    return True
                user = data.get("userInfo", {}).get("user")
                if user and user.get("uniqueId"):
                    return False
                return True
            return None
    except Exception:
        return None


async def _check_snapchat(session, username):
    """Snapchat — باستخدام API الاقتراحات"""
    try:
        url = ("https://accounts.snapchat.com/accounts/get_username_suggestions"
               "?requested_username=" + username + "&xsrf_token=")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                try:
                    data = await resp.json()
                except Exception:
                    return None
                status_code = data.get("reference", {}).get("status_code", "")
                if status_code == "OK":
                    return True
                elif status_code == "TAKEN":
                    return False
            return None
    except Exception:
        return None


async def _check_telegram(session, username):
    """Telegram — بالمؤشرات"""
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

                has_title = "tgme_page_title" in text
                has_extra = "tgme_page_extra" in text

                if has_title and has_extra:
                    return False

                if "If you have Telegram, you can contact" in text and not has_title:
                    return True

                return None
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


# ─── خريطة المنصات (بدون GitHub) ───
_PLATFORM_CHECKERS = {
    "Reddit": _check_reddit,
    "Instagram": _check_instagram,
    "TikTok": _check_tiktok,
    "Snapchat": _check_snapchat,
    "Telegram": _check_telegram,
}


async def check_username_all_platforms(session, username, platforms):
    """يفحص اسم واحد على كل المنصات بالتوازي"""
    async def run_check(platform):
        checker = _PLATFORM_CHECKERS.get(platform)
        if not checker:
            return platform, None
        try:
            result = await checker(session, username)
            return platform, result
        except Exception as e:
            log.warning("خطأ في %s لـ %s: %s", platform, username, str(e)[:100])
            return platform, None

    tasks = [run_check(p) for p in platforms]
    results = await asyncio.gather(*tasks)

    data = {"available": [], "taken": [], "unknown": []}
    for platform, result in results:
        if result is True:
            data["available"].append(platform)
        elif result is False:
            data["taken"].append(platform)
        else:
            data["unknown"].append(platform)

    return data


async def check_usernames_availability(usernames: list,
                                        platforms: list) -> dict:
    """يفحص قائمة أسماء على المنصات (بالتوازي)"""
    results = {}

    async with aiohttp.ClientSession() as session:
        # نفحص عدة أسماء بالتوازي (أسرع)
        tasks = [
            check_username_all_platforms(session, u, platforms)
            for u in usernames
        ]
        results_list = await asyncio.gather(*tasks)

        for username, data in zip(usernames, results_list):
            results[username] = data

    return results


# ═══════════════════════════════════════════════════════════════
# 🔄 توليد المتاح فقط (مع تحسين للوصول لـ 15)
# ═══════════════════════════════════════════════════════════════

async def generate_available_usernames(description: str,
                                        count: int,
                                        max_length: int,
                                        platforms: list,
                                        max_rounds: int = 6):
    """
    يولّد أسماء متاحة (ليست محجوزة على أي منصة)
    - 6 جولات كحد أقصى للوصول للعدد المطلوب
    - يطلب عدد كبير من الأسماء في كل جولة
    """
    available = []
    seen = set()

    for round_num in range(max_rounds):
        needed = count - len(available)
        if needed <= 0:
            break

        # نطلب أكثر بكثير لضمان الوصول
        request_count = min(max(needed * 4, 20), 30)

        log.info("الجولة %d: نولّد %d اسم عشان نكمل %d",
                 round_num + 1, request_count, needed)

        candidates = await generate_usernames_with_ai(
            description, count=request_count, max_length=max_length
        )

        candidates = [c for c in candidates if c not in seen]
        seen.update(candidates)

        if not candidates:
            log.warning("AI ما رجّع أسماء")
            continue

        log.info("نفحص %d اسم...", len(candidates))
        results = await check_usernames_availability(candidates, platforms)

        for name, data in results.items():
            # لو محجوز على أي منصة -> تجاهل
            if data["taken"]:
                continue
            # لازم متاح على منصة واحدة على الأقل (مو كلها unknown)
            if not data["available"]:
                continue

            if len(available) < count:
                available.append((name, data))

        log.info("بعد الجولة %d: عندنا %d متاح",
                 round_num + 1, len(available))

    return available


# ═══════════════════════════════════════════════════════════════
# ⚙️ الأمر
# ═══════════════════════════════════════════════════════════════

def register_command(bot):
    """تسجيل أمر /اكتشف_يوزر"""

    @bot.tree.command(name="اكتشف_يوزر",
                      description="يولّد 15 يوزر متاح (يستبعد المحجوز على أي منصة)")
    @app_commands.describe(
        وصف="وصف اختياري",
        حرف="حرف محدد a-z",
        عدد="عدد الأسماء المتاحة (1-15، افتراضي: 15)",
        طول="الحد الأقصى لطول الاسم (2-5، افتراضي: 5)",
    )
    async def discover_username_cmd(interaction: discord.Interaction,
                                     وصف: str = "",
                                     حرف: str = "",
                                     عدد: int = 15,
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

        if عدد < 1 or عدد > 15:
            await interaction.response.send_message(
                "العدد بين 1 و 15.", ephemeral=True
            )
            return

        if طول < 2 or طول > 5:
            await interaction.response.send_message(
                "الطول بين 2 و 5.", ephemeral=True
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
                            ["Reddit", "Instagram", "TikTok", "Snapchat", "Telegram"])

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

        embed = discord.Embed(
            title=title,
            description=(
                "🎯 **العدد:** " + str(len(available)) + " من " + str(عدد) + "\n"
                "🌐 **الفحص عبر:** " + ", ".join(platforms)
            ),
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        for name, data in available[:15]:
            avail = data["available"]
            unknown = data["unknown"]

            if len(avail) == len(platforms):
                icon = "🌟"
            elif len(avail) >= 2:
                icon = "✅"
            else:
                icon = "🔸"

            # سطر الحالة
            platform_parts = []
            for p in platforms:
                if p in avail:
                    platform_parts.append("✅ " + p)
                elif p in unknown:
                    platform_parts.append("❔ " + p)

            detail = " • ".join(platform_parts)

            embed.add_field(
                name=icon + " `" + name + "`",
                value=detail,
                inline=False,
            )

        embed.set_footer(text="✅ = متاح | ❔ = ما قدرنا نتحقق")

        await interaction.followup.send(embed=embed)

    log.info("✅ تم تسجيل أمر /اكتشف_يوزر")


def load_usernames(bot, shared: dict):
    SHARED.clear()
    SHARED.update(shared)

    if not getattr(config, "USERNAME_FINDER_ENABLED", True):
        log.info("ميزة اليوزرات معطلة")
        return

    register_command(bot)
    log.info("✅ تم تحميل usernames.py")
