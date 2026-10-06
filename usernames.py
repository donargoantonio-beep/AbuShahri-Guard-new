# ═══════════════════════════════════════════════════════════════
# 🔎 usernames.py -- ميزة اكتشاف اليوزرات بالذكاء الاصطناعي
# ═══════════════════════════════════════════════════════════════
"""
ميزة مستقلة:
- Gemini AI لتوليد الأسماء
- socialscan لفحص التوفر
- تعمل فقط في روم محدد
- متاحة للجميع
"""
import re
import asyncio
import logging

import discord
from discord import app_commands

import config

log = logging.getLogger("usernames")

SHARED: dict = {}

_gemini_model = None


def _init_gemini():
    """تهيئة Gemini (مرة واحدة)"""
    global _gemini_model

    if _gemini_model is not None:
        return _gemini_model

    if not config.GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY غير موجود")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=config.GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        log.info("تم تهيئة Gemini بنجاح")
        return _gemini_model
    except ImportError:
        log.error("google-generativeai غير مثبتة")
        return None
    except Exception as e:
        log.error("فشل تهيئة Gemini: %s", e)
        return None


async def generate_usernames_with_ai(description: str,
                                      count: int = 10,
                                      max_length: int = 5) -> list:
    """يولّد أسماء مستخدمين قصيرة بالـ AI"""
    model = _init_gemini()
    if not model:
        return []

    prompt = (
        "You are an expert at suggesting SHORT English usernames.\n\n"
        "TASK: Generate " + str(count) + " English usernames.\n\n"
        "RULES:\n"
        "1. Each username must be " + str(max_length) + " letters or fewer\n"
        "2. Use REAL English words (nouns, verbs, adjectives)\n"
        "3. Include a MIX of starting letters from A-Z\n"
        "4. All lowercase, no numbers, no symbols, no spaces\n"
        "5. Diverse (not all same theme)\n"
        "6. Prefer common, memorable words\n\n"
        "EXAMPLES:\n"
        "ace, arc, art, ash, bay, bee, bit, box, bug, cap, car, cat,\n"
        "cod, cow, cry, cut, day, dew, dog, dot, dry, elf, end, eye,\n"
        "fan, far, fig, fin, fix, fly, fog, fox, fry, fun, fur, gap,\n"
        "gem, god, gum, gun, guy, gym, hat, hen, hex, hit, hub, ice,\n"
        "ink, ivy, jam, jaw, jet, joy, key, kid, kit, lab, lap, law,\n"
        "leg, log, low, map, mat, may, mix, mud, nap, net, new, nod,\n"
        "nut, oak, odd, oil, old, owl, pan, paw, pen, pet, pie, pig,\n"
        "pin, pit, pot, pro, pup, rat, raw, red, rib, rip, rob, rod,\n"
        "row, rub, rug, run, sad, saw, sea, set, shy, sin, sip, sir,\n"
        "sit, six, ski, sky, sly, son, spy, sun, tag, tap, tax, tea,\n"
        "ten, tie, tin, tip, toe, ton, top, toy, try, tub, tug, two,\n"
        "van, war, wax, way, web, wet, win, wit, wow, yes, yet, you,\n"
        "zap, zip, zoo\n\n"
        "OPTIONAL THEME: " + (description or "none") + "\n\n"
        "OUTPUT: Return ONLY the usernames, one per line, no numbering, "
        "no explanations, no dashes, no quotes."
    )

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()

        names = []
        for line in text.split("\n"):
            name = line.strip().strip("-").strip("*").strip().strip('"').strip("'")
            name = name.replace("`", "").strip()
            if name and name.isascii() and name.isalnum():
                if 2 <= len(name) <= max_length:
                    names.append(name.lower())

        names = list(dict.fromkeys(names))[:count]
        return names

    except Exception as e:
        log.error("فشل توليد الأسماء: %s", e)
        return []


async def check_usernames_availability(usernames: list,
                                        platforms: list) -> list:
    """يفحص توفر عدة أسماء عبر socialscan"""
    try:
        from socialscan.util import Platforms, sync_execute_queries

        platform_map = {
            "Instagram": Platforms.INSTAGRAM,
            "Twitter":   Platforms.TWITTER,
            "Snapchat":  Platforms.SNAPCHAT,
            "Reddit":    Platforms.REDDIT,
            "Pinterest": Platforms.PINTEREST,
            "GitHub":    Platforms.GITHUB,
        }

        selected = [platform_map[p] for p in platforms if p in platform_map]
        if not selected:
            return []

        results = await asyncio.to_thread(
            sync_execute_queries, usernames, selected
        )
        return results

    except ImportError:
        log.error("socialscan غير مثبتة")
        return []
    except Exception as e:
        log.error("خطأ في الفحص: %s", e)
        return []


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
                "فشل توليد الأسماء. تأكد من GEMINI_API_KEY."
            )
            return

        platforms = getattr(config, "USERNAME_FINDER_PLATFORMS",
                            ["Instagram", "Twitter", "Snapchat"])
        results = await check_usernames_availability(candidates, platforms)

        if not results:
            await interaction.followup.send(
                "تم التوليد لكن فشل الفحص. تأكد من socialscan."
            )
            return

        by_username = {}
        for r in results:
            if r.query not in by_username:
                by_username[r.query] = {"available": [], "taken": [], "unknown": []}

            platform_name = str(r.platform).replace("Platforms.", "").capitalize()

            if r.available is True:
                by_username[r.query]["available"].append(platform_name)
            elif r.available is False:
                by_username[r.query]["taken"].append(platform_name)
            else:
                by_username[r.query]["unknown"].append(platform_name)

        def sort_key(p):
            try:
                return platforms.index(p)
            except ValueError:
                return 999

        for u in by_username:
            by_username[u]["available"].sort(key=sort_key)
            by_username[u]["taken"].sort(key=sort_key)
            by_username[u]["unknown"].sort(key=sort_key)

        def name_score(n):
            data = by_username[n]
            return (len(data["available"]) * 100 - len(data["taken"]) * 10
                    + (100 if not data["taken"] else 0))

        sorted_names = sorted(by_username.keys(), key=name_score, reverse=True)

        total = len(platforms)
        fully_available = sum(
            1 for n in sorted_names
            if len(by_username[n]["available"]) == total
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
            data = by_username[name]
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

    log.info("تم تسجيل أمر /اكتشف_يوزر")


def load_usernames(bot, shared: dict):
    """نقطة التحميل"""
    SHARED.clear()
    SHARED.update(shared)

    if not getattr(config, "USERNAME_FINDER_ENABLED", True):
        log.info("ميزة اليوزرات معطلة")
        return

    register_command(bot)
    log.info("تم تحميل usernames.py")
