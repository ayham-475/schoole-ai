import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from rapidfuzz import process, fuzz

# ==========================================
# 1. تعريف الهياكل الأساسية (Data Structures)
# ==========================================

class Intent(Enum):
    QUERY_SCHEDULE = "query_schedule"
    QUERY_TEACHER = "query_teacher"
    QUERY_CURRICULUM = "query_curriculum"
    QUERY_EVENTS = "query_events_calendar"
    QUERY_RULES = "query_rules_policy"
    UNKNOWN = "fallback_unknown"

@dataclass
class NLPResult:
    intent: str
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0

# ==========================================
# 2. الفئة الرئيسية لمعالجة اللغة الطبيعية
# ==========================================

class NLPProcessor:
    """
    محرك تحليل اللغة الطبيعية (NLP Processor).
    يصنف نية المستخدم (Intent) ويستخرج الكيانات (Entities) من النص المعالج.
    """
    
    def __init__(self):
        # قواميس الكلمات المفتاحية لتحديد النوايا (Intents)
        self.intent_keywords = {
            Intent.QUERY_SCHEDULE: ["جدول", "حصه", "حصص", "ماده", "بدرس", "متي حصه", "الجدول"],
            Intent.QUERY_TEACHER: ["معلم", "استاذ", "دكتور", "مكتب", "ساعات", "تواصل", "رئيس قسم"],
            Intent.QUERY_CURRICULUM: ["منهج", "كتاب", "مقرر", "وحده", "مواضيع", "دروس"],
            Intent.QUERY_EVENTS: ["تقويم", "عطله", "اجازه", "امتحانات", "فعاليه", "رحله", "نادي", "مسابقه"],
            Intent.QUERY_RULES: ["غياب", "تاخير", "عذر", "درجات", "اعاده", "شرف", "مخالفه", "عقوبه", "قبول", "تحويل"]
        }

        # خرائط استخراج الكيانات (Entities Maps) - مطابقة للـ IDs في الـ JSON
        self.days_map = {
            "احد": "Sunday", "اثنين": "Monday", "ثلاثاء": "Tuesday", 
            "اربعاء": "Wednesday", "خميس": "Thursday"
        }
        
        self.grades_map = {
            "اول": "GRADE_10", "عاشر": "GRADE_10",
            "ثاني": "GRADE_11", "حادي عشر": "GRADE_11",
            "ثالث": "GRADE_12", "ثاني عشر": "GRADE_12", "توجيهي": "GRADE_12"
        }

        self.periods_map = {
            "اولي": "P_01", "ثانيه": "P_02", "ثالثه": "P_03",
            "رابعه": "P_04", "خامسه": "P_05", "سادسه": "P_06", "طابور": "P_ASSEMBLY"
        }
        
        # قائمة المواد للبحث الضبابي (Fuzzy Search)
        self.known_subjects = ["رياضيات", "فيزياء", "كيمياء", "عربي", "انجليزي", "حاسب", "ذكاء اصطناعي", "اسلاميه"]

    def process_query(self, normalized_text: str) -> NLPResult:
        """
        المسار الرئيسي: يأخذ النص الموحد ويرجع النية والكيانات.
        """
        intent = self._classify_intent(normalized_text)
        entities = self._extract_entities(normalized_text)
        
        return NLPResult(
            intent=intent.value,
            entities=entities,
            confidence=0.9 if intent != Intent.UNKNOWN else 0.1
        )

    def _classify_intent(self, text: str) -> Intent:
        """يصنف نية المستخدم بناءً على تقاطع الكلمات المفتاحية."""
        words = set(text.split())
        best_intent = Intent.UNKNOWN
        max_matches = 0

        for intent, keywords in self.intent_keywords.items():
            # حساب عدد الكلمات المتقاطعة بين النص ومفردات النية
            matches = sum(1 for kw in keywords if kw in text or any(fuzz.ratio(kw, w) > 85 for w in words))
            if matches > max_matches:
                max_matches = matches
                best_intent = intent

        return best_intent

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """يستخرج الكيانات المطلوبة (الأيام، الصفوف، الحصص، المواد)."""
        entities = {}

        # 1. استخراج اليوم
        for ar_day, en_day in self.days_map.items():
            if ar_day in text:
                entities["day"] = en_day
                break

        # 2. استخراج المرحلة/الصف (Grade)
        for ar_grade, grade_id in self.grades_map.items():
            if ar_grade in text:
                entities["grade_id"] = grade_id
                break

        # 3. استخراج رقم الحصة (Period)
        for ar_period, period_id in self.periods_map.items():
            if ar_period in text:
                entities["period_id"] = period_id
                break

        # 4. استخراج الشعبة باستخدام Regex (مثل: 3/1 أو 1/ا)
        class_match = re.search(r'\b(\d)\s*/\s*([ا-ي\d])\b', text)
        if class_match:
            # تنظيف وتنسيق الشعبة ليطابق الـ IDs لاحقاً
            entities["class_raw"] = f"{class_match.group(1)}/{class_match.group(2)}"

        # 5. استخراج اسم المادة باستخدام RapidFuzz لمعالجة الأخطاء الإملائية
        # مثال: إذا كتب المستخدم "رياظيات"، سيتعرف عليها كـ "رياضيات"
        extracted_subject = process.extractOne(
            text, 
            self.known_subjects, 
            scorer=fuzz.partial_token_sort_ratio, 
            score_cutoff=75  # الحد الأدنى للتطابق 75%
        )
        if extracted_subject:
            entities["subject"] = extracted_subject[0] # الكلمة المطابقة

        return entities

# ==========================================
# اختبار سريع للوحدة (Quick Test)
# ==========================================
if __name__ == "__main__":
    from arabic_normalizer import ArabicNormalizer
    
    normalizer = ArabicNormalizer()
    nlp = NLPProcessor()
    
    # محاكاة لاستعلامات مستخدمين بأشكال مختلفة
    queries = [
        "متي حصه الرياظيات للصف الثالث الثانوي يوم الاحد؟", # خطأ إملائي مقصود (الرياظيات)
        "ايش عقوبه الغياب بدون عذر؟",
        "وين مكتب استاذ احمد؟"
    ]
    
    print("--- اختبار محرك NLP ---")
    for q in queries:
        norm_q = normalizer.normalize(q)
        result = nlp.process_query(norm_q)
        print(f"الاستعلام الأصلي: {q}")
        print(f"النص المعالج  : {norm_q}")
        print(f"النية (Intent): {result.intent}")
        print(f"الكيانات      : {result.entities}")
        print("-" * 40)