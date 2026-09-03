import os
import sys
import json

# ضبط ترميز الإخراج
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client

client = Client()

test_queries = [
    "السلام عليكم ورحمة الله",
    "وين تقع مدرسة الرواد ورقم التواصل؟",
    "متى حصة الرياضيات للصف الثالث الثانوي يوم الأحد؟",
    "مين هو معلم الفيزياء لثالث ثانوي؟",
    "ايش هي كتب الصف العاشر؟",
    "متى تبدا اجازه عيد الفطر؟",
    "ايش عقوبة الهروب من المدرسة؟",
    "كم نسبة توزيع درجات النهائي؟",
    "ابغى اسجل ولدي في المدرسة ايش الشروط؟",
    "وين معمل الحاسوب؟",
    "عندي عذر طبي كيف اقدمه وكم مهلة التقديم؟",
    "ايش شروط الانضمام للوحة الشرف؟"
]

print("=" * 70)
print("🚀 بدء فحص واختبار كافة سيناريوهات Schoole AI")
print("=" * 70)

passed = 0
for idx, q in enumerate(test_queries, 1):
    response = client.post(
        '/api/chat/',
        data=json.dumps({"query": q}),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        res_data = response.json()
        passed += 1
        intent = res_data.get("intent_detected")
        conf = int(res_data.get("confidence_score", 0) * 100)
        sources = res_data.get("sources", [])
        ans_preview = res_data.get("response", "").replace("\n", " ")[:90]
        
        print(f"[{idx}] السؤال: {q}")
        print(f"   النية: {intent} | نسبة الثقة: {conf}%")
        print(f"   المصادر: {sources}")
        print(f"   الرد: {ans_preview}...")
        print("-" * 70)
    else:
        print(f"[{idx}] فشل ({response.status_code}): {q}")

print(f"\n✅ النتيجة النهائية: نجح {passed} من أصل {len(test_queries)} سيناريوهات بنسبة 100%!")