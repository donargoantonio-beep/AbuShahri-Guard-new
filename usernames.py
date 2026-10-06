# ═══════════════════════════════════════════════════════════════
# 🔎 usernames.py -- إصدار 7.0 (دفعات متتالية)
# ═══════════════════════════════════════════════════════════════
import asyncio
import logging
import time

import aiohttp
import discord
from discord import app_commands

import config

log = logging.getLogger("usernames")

SHARED: dict = {}

# ─── إعدادات الأداء ───
_MAX_CONCURRENT = 25
_REQUEST_TIMEOUT = 5


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
        "temperature": 1.0,
        "max_tokens": 4096,
    }

    async with session.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=aiohttp.ClientTimeout(total=25),
    ) as resp:
        if resp.status != 200:
            return None, resp.status
        data = await resp.json()
        return data["choices"][0]["message"]["content"], 200


async def generate_usernames_with_ai(description: str,
                                      count: int = 50,
                                      max_length: int = 5) -> list:
    if not config.GROQ_API_KEY:
        return []

    prompt = (
        "Generate exactly " + str(count) + " unique short English usernames, "
        + str(max_length) + " letters or fewer each. "
        "Use REAL English words (nouns, verbs, adjectives), all lowercase, "
        "no numbers, no symbols, no spaces. "
        "Maximum diversity (different starting letters, different themes). "
        "Theme: " + (description or "diverse memorable words") + ". "
        "Return ONLY the usernames, one per line. "
        "Output exactly " + str(count) + " lines, nothing else."
    )

    text = None
    try:
        async with aiohttp.ClientSession() as session:
            for model_name in _GROQ_MODELS:
                try:
                    result, status = await _call_groq(session, model_name, prompt)
                    if status == 200 and result:
                        log.info("✅ نجح الموديل: %s", model_name)
                        text = result
                        break
                except Exception as e:
                    log.warning("خطأ في %s: %s", model_name, str(e)[:100])
                    continue

        if not text:
            return []

        names = []
        for line in text.split("\n"):
            name = line.strip().strip("-*\"'`.").strip()
            name = name.lstrip("0123456789. ").strip()
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
    try:
        url = "https://www.reddit.com/user/" + username + "/about.json"
        headers = {"User-Agent": "Mozilla/5.0 DiscordBot/1.0"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)) as resp:
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
    try:
        url = ("https://www.instagram.com/api/v1/users/web_profile_info/"
               "?username=" + username)
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X)",
            "X-IG-App-ID": "936619743392459",
            "Accept": "*/*",
        }
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)) as resp:
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
    try:
        url = ("https://www.tiktok.com/oembed?url="
               "https://www.tiktok.com/@" + username)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)) as resp:
            if resp.status == 200:
                return False
            elif resp.status in (400, 404):
                return True
            return None
    except Exception:
        return None


async def _check_snapchat(session, username):
    try:
        url = ("https://accounts.snapchat.com/accounts/get_username_suggestions"
               "?requested_username=" + username + "&xsrf_token=")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        }
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT)) as resp:
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
    try:
        url = "https://t.me/" + username
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with session.get(url, headers=headers,
                                timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT),
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
                if "If you have Telegram" in text and not has_title:
                    return True
                return None
            elif resp.status == 404:
                return True
            return None
    except Exception:
        return None


_PLATFORM_CHECKERS = {
    "Reddit": _check_reddit,
    "Instagram": _check_instagram,
    "TikTok": _check_tiktok,
    "Snapchat": _check_snapchat,
    "Telegram": _check_telegram,
}


# ═══════════════════════════════════════════════════════════════
# 🔒 Semaphore
# ═══════════════════════════════════════════════════════════════

_check_semaphore = asyncio.Semaphore(_MAX_CONCURRENT)


async def _safe_check(session, username, platform):
    checker = _PLATFORM_CHECKERS.get(platform)
    if not checker:
        return platform, None

    async with _check_semaphore:
        try:
            result = await checker(session, username)
            return platform, result
        except Exception:
            return platform, None


async def check_username_all_platforms(session, username, platforms):
    tasks = [_safe_check(session, username, p) for p in platforms]
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


async def check_usernames_batch(session, usernames, platforms):
    tasks = [check_username_all_platforms(session, u, platforms) for u in usernames]
    results = await asyncio.gather(*tasks)
    return dict(zip(usernames, results))


# ═══════════════════════════════════════════════════════════════
# 🔄 المولّد الرئيسي (يدعم دفعات)
# ═══════════════════════════════════════════════════════════════

async def stream_available_usernames(
    description: str,
    total_needed: int,
    batch_size: int,
    max_length: int,
    platforms: list,
    on_batch_callback,
):
    """
    يولّد أسماء متاحة ويستدعي on_batch_callback كل ما جمع batch_size
    يتوقف عند total_needed
    """
    delivered = 0
    seen = set()
    start_time = time.time()

    # حد أقصى للجولات (يمنع اللوب اللانهائي)
    max_iterations = 40
    empty_rounds = 0

    for iteration in range(max_iterations):
        if delivered >= total_needed:
            break

        # كم باقي
        still_need = total_needed - delivered
        # نطلب كمية كافية + هامش للرفض
        request_count = min(max(still_need * 4, 30), 80)

        log.info("جولة %d: نحتاج %d، نطلب %d من AI",
                 iteration + 1, still_need, request_count)

        candidates = await generate_usernames_with_ai(
            description,
            count=request_count,
            max_length=max_length,
        )

        candidates = [c for c in candidates if c not in seen]
        seen.update(candidates)

        if not candidates:
            empty_rounds += 1
            if empty_rounds >= 5:
                log.warning("5 جولات فاضية — نوقف")
                break
            continue

        empty_rounds = 0

        # فحص الدفعة
        log.info("نفحص %d اسم...", len(candidates))

        async with aiohttp.ClientSession() as session:
            results = await check_usernames_batch(session, candidates, platforms)

        # اجمع المتاح
        batch_buffer = []

        for name, data in results.items():
            if data["taken"]:
                continue
            if not data["available"]:
                continue

            batch_buffer.append((name, data))

            # لو وصلنا للدفعة — أرسلها
            if len(batch_buffer) >= batch_size:
                remaining_global = total_needed - delivered
                to_send = batch_buffer[:batch_size]
                if len(to_send) > remaining_global:
                    to_send = to_send[:remaining_global]

                await on_batch_callback(
                    to_send,
                    delivered + len(to_send),
                    total_needed,
                    time.time() - start_time,
                )

                delivered += len(to_send)
                batch_buffer = batch_buffer[len(to_send):]

                if delivered >= total_needed:
                    break

        # أرسل أي بقايا (لو وصلنا للنهاية)
        if batch_buffer and delivered < total_needed:
            remaining_global = total_needed - delivered
            to_send = batch_buffer[:remaining_global]

            if to_send:
                await on_batch_callback(
                    to_send,
                    delivered + len(to_send),
                    total_needed,
                    time.time() - start_time,
                )
                delivered += len(to_send)

    log.info("انتهى! %d / %d | الوقت: %.1fث",
             delivered, total_needed, time.time() - start_time)

    return delivered


# ═══════════════════════════════════════════════════════════════
# 🎨 بناء إيمبد لكل دفعة
# ═══════════════════════════════════════════════════════════════

def _build_batch_embed(batch: list, platforms: list,
                       delivered: int, total: int,
                       elapsed: float, letter: str) -> discord.Embed:
    total_platforms = len(platforms)

    title = "🔎 يوزرات متاحة — " + str(delivered) + " / " + str(total)
    if letter:
        title = "🔎 حرف " + letter.upper() + " — " + str(delivered) + " / " + str(total)

    embed = discord.Embed(
        title=title,
        description=(
            "🌐 " + ", ".join(platforms) + "\n"
            "⏱️ " + str(int(elapsed)) + " ثانية"
        ),
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )

    for name, data in batch:
        avail = data["available"]
        unknown = data["unknown"]

        if len(avail) == total_platforms:
            icon = "🌟"
        elif len(avail) >= 3:
            icon = "✅"
        elif len(avail) >= 1:
            icon = "🔸"
        else:
            icon = "❔"

        parts = []
        for p in platforms:
            if p in avail:
                parts.append("✅" + p)
            elif p in unknown:
                parts.append("❔" + p)

        detail = " • ".join(parts)

        embed.add_field(
            name=icon + " `" + name + "`",
            value=detail,
            inline=False,
        )

    embed.set_footer(text="✅ = مؤكد متاح | ❔ = ما قدرنا نتحقق")

    return embed


# ═══════════════════════════════════════════════════════════════
# ⚙️ الأمر
# ═══════════════════════════════════════════════════════════════

def register_command(bot):

    @bot.tree.command(name="اكتشف_يوزر",
                      description="يولّد يوزرات بكميات كبيرة — رسائل متفرقة")
    @app_commands.describe(
        وصف="وصف اختياري",
        حرف="حرف محدد a-z",
        عدد="العدد الإجمالي (1-500، افتراضي: 100)",
        كل="عدد اليوزرات في كل رسالة (5-25، افتراضي: 15)",
        طول="الحد الأقصى لطول الاسم (2-5، افتراضي: 5)",
    )
    async def discover_username_cmd(interaction: discord.Interaction,
                                     وصف: str = "",
                                     حرف: str = "",
                                     عدد: int = 100,
                                     كل: int = 15,
                                     طول: int = 5):

        if not getattr(config, "USERNAME_FINDER_ENABLED", True):
            await interaction.response.send_message(
                "الميزة معطلة حالياً.", ephemeral=True
            )
            return

        allowed_channel_id = getattr(config, "USERNAME_FINDER_CHANNEL_ID", 0)
        if allowed_channel_id and interaction.channel_id != allowed_channel_id:
            await interaction.response.send_message(
                "هذا الأمر يعمل فقط في <#" + str(allowed_channel_id) + ">.",
                ephemeral=True
            )
            return

        # تحقق من الأرقام
        if عدد < 1 or عدد > 500:
            await interaction.response.send_message(
                "العدد بين 1 و 500.", ephemeral=True
            )
            return

        if كل < 5 or كل > 25:
            await interaction.response.send_message(
                "الكمية في كل رسالة بين 5 و 25.", ephemeral=True
            )
            return

        if طول < 2 or طول > 5:
            await interaction.response.send_message(
                "الطول بين 2 و 5.", ephemeral=True
            )
            return

        # معالجة الحرف
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

        # رسالة البداية
        estimated_batches = (عدد + كل - 1) // كل
        await interaction.followup.send(
            "🚀 **بدأ البحث**\n"
            "🎯 **العدد:** " + str(عدد) + "\n"
            "📦 **كل رسالة:** " + str(كل) + " يوزر\n"
            "📨 **عدد الرسائل:** ~" + str(estimated_batches) + "\n"
            "🌐 **المنصات:** " + ", ".join(platforms) + "\n\n"
            "⏳ **البوت راح يرسل الرسائل تدريجياً...**"
        )

        # callback الإرسال
        async def send_batch(batch, delivered, total, elapsed):
            try:
                embed = _build_batch_embed(
                    batch, platforms, delivered, total, elapsed, letter
                )
                await interaction.followup.send(embed=embed)
                log.info("📨 أرسلنا دفعة %d/%d", delivered, total)
            except Exception as e:
                log.warning("فشل إرسال دفعة: %s", e)

        # ابدأ البحث
        total_delivered = await stream_available_usernames(
            description=وصف,
            total_needed=عدد,
            batch_size=كل,
            max_length=طول,
            platforms=platforms,
            on_batch_callback=send_batch,
        )

        # رسالة النهاية
        await interaction.followup.send(
            "✅ **انتهى البحث**\n"
            "📊 **المُسلَّم:** " + str(total_delivered) + " / " + str(عدد) + "\n"
            "🎉 شكراً لاستخدامك!"
        )

    log.info("✅ تم تسجيل أمر /اكتشف_يوزر")


def load_usernames(bot, shared: dict):
    SHARED.clear()
    SHARED.update(shared)

    if not getattr(config, "USERNAME_FINDER_ENABLED", True):
        log.info("ميزة اليوزرات معطلة")
        return

    register_command(bot)
    log.info("✅ تم تحميل usernames.py")
