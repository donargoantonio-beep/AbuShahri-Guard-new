# config.py

# الأيديات المصرح لها بالتحكم المطلق بالبوت (أيديك الشخصي)
OWNER_IDS = [
    813236200142929950,
]

# آيدي رتبة "النائب" (إن وجد، وإلا اتركها 0)
OWNER_ROLE_ID = 0  

# أسماء الرومات والرتب التي سيقوم البوت بإنشائها تلقائياً
QUARANTINE_CHANNEL_NAME = "quarantine"     # روم الحجر الصحي (بالإنجليزية)
QUARANTINE_ROLE_NAME = "محجور"             # رتبة الحجر (تنسحب باقي الرومات وتبقى هذه فقط)

TICKET_CATEGORY_NAME = "Tickets System"    # كاتيجوري التذاكر
ADMIN_REVIEW_CHANNEL_NAME = "admin-review" # روم مراجعة الإدارة للتقديمات والتذاكر

SUPPORT_ROLE_NAME = "Support Team"         # رتبة الدعم للتذاكر
APPLY_STAFF_ROLE_NAME = "Staff Manager"    # رتبة مسؤولي التقديمات

# الرتب المحمية من العبث (ضع أيديات رتب الإدارة المهمة هنا لكي يحميه البوت)
PROTECTED_ROLE_IDS = [
    # 000000000000000000, 
]

# رسائل اللوحات
TICKET_PANEL_TITLE = "🎟️ نظام التذاكر والدعم الفني"
TICKET_PANEL_DESC = "اضغط على الزر بالأسفل لفتح تذكرة جديدة وسيقوم فريق الدعم بمساعدتك."
TICKET_BUTTON_LABEL = "فتح تذكرة 🎫"
TICKET_WELCOME_MSG = "أهلاً بك! يرجى توضيح مشكلتك وسنتحقق منها بأقرب وقت."

APPLY_MODAL_TITLE = "📝 استمارة التقديم للإدارة"
QUESTION_1 = "ما هو اسمك أو لقبك في الديسكورد؟"
QUESTION_2 = "كم عمرك؟"
QUESTION_3 = "لماذا تريد الانضمام لفريقنا وما هي خبراتك؟"
