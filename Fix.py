"""
fix.py — يصلح الأحرف العربية الذكية في كل الملفات
شغّله مرة واحدة فقط
"""
import os

# الأحرف المشكلة → الحل الصحيح
REPLACEMENTS = {
    "→": "->",       # سهم عربي
    "←": "<-",       # سهم عربي
    "’": "'",        # اقتباس ذكي
    "‘": "'",        # اقتباس ذكي
    "“": '"',        # اقتباس مزدوج ذكي
    "”": '"',        # اقتباس مزدوج ذكي
    "—": "--",       # شرطة طويلة
    "–": "-",        # شرطة متوسطة
    "…": "...",      # نقاط
    " ": " ",        # مسافة غير قابلة للكسر (nbsp)
}

FILES = ["main.py", "extras.py", "config.py", "keep_alive.py"]

print("=" * 50)
print("🔧 إصلاح الأحرف العربية الذكية")
print("=" * 50)

total_fixed = 0

for filename in FILES:
    if not os.path.exists(filename):
        print(f"⏭️  تخطي {filename} (غير موجود)")
        continue

    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    fixes_count = 0
    for bad, good in REPLACEMENTS.items():
        count = content.count(bad)
        if count > 0:
            content = content.replace(bad, good)
            fixes_count += count
            print(f"   • {filename}: استبدلت '{bad}' → '{good}' ({count} مرة)")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    if fixes_count > 0:
        print(f"✅ {filename}: تم إصلاح {fixes_count} حرف")
        total_fixed += fixes_count
    else:
        print(f"✅ {filename}: نظيف (لا يحتاج تعديل)")

print("=" * 50)
print(f"🎉 المجموع: {total_fixed} حرف تم إصلاحه")
print("=" * 50)
print("\n✅ الآن شغّل البوت عادي: python main.py")
