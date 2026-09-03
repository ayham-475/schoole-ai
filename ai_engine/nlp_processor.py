import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from rapidfuzz import process, fuzz


# ==========================================
# 1. تعريف النوايا الشاملة (Intents)
# ==========================================

class Intent(Enum):
    GREETING = "greeting"
    SCHOOL_INFO = "school_info"
    QUERY_SCHEDULE = "query_schedule"
    QUERY_TEACHER = "query_teacher"
    QUERY_CURRICULUM = "query_curriculum"
    QUERY_CALENDAR = "query_events_calendar"
    QUERY_EXAMS = "query_exams"
    QUERY_ACTIVITIES = "query_activities"
    QUERY_COMPETITIONS = "query_competitions"
    QUERY_ATTENDANCE = "query_attendance_policy"
    QUERY_GRADING = "query_evaluation_policy"
    QUERY_DISCIPLINE = "query_rules_policy"
    QUERY_ADMISSION = "query_admission_policy"
    QUERY_FACILITIES = "query_facilities"
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
    محرك تحليل اللغة الطبيعية المتقدم (Advanced NLP Processor).
    - يدعم 14 نية تغطي كامل بيئة المدرسة وقواعد المعرفة.
    - يحتوي على أكثر من 250 كلمة مفتاحية ومرادفاً بالفصحى والعامية.
    - استخراج كيانات متعدد (اليوم، الصف، الشعبة، الحصة، المادة، المعلم، المرفق).
    - حساب مرن لدرجة الثقة (Confidence Score).
    """

    def __init__(self):
        # 1. قواميس الكلمات المفتاحية مع أوزان دلالية
        self.intent_keywords = {
            Intent.GREETING: [
                "مرحبا", "السلام عليكم", "اهلا", "اهلين", "صباح الخير", "مساء الخير",
                "هلا", "سلام", "حيياك", "حياك", "تحياتي", "مرحبتين"
            ],
            Intent.SCHOOL_INFO: [
                "عن المدرسه", "نبذه", "من انتم", "اسم المدرسه", "رويه", "رساله",
                "مدير المدرسه", "موقع المدرسه", "اين تقع", "عنوان المدرسه", "رقم المدرسه",
                "هاتف", "تلفون", "ايميل المدرسه", "موقع الكتروني", "ساعات الدوام",
                "مواعيد العمل", "باصات", "مواصلات", "مقصف", "تغذيه", "مميزات المدرسه",
                "خصائص", "خدمات الطلاب", "تاريخ التاسيس", "الرواد النموذجيه", "المدير العام",
                "معلومات المدرسه"
            ],
            Intent.QUERY_SCHEDULE: [
                "جدول", "حصه", "حصص", "الجدول الاسبوعي", "جدول الحصص", "حصه الرياضه",
                "حصه الرياضيات", "حصه الفيزياء", "متي تبدا الحصه", "طابور الصباح", "الفسحه"
            ],
            Intent.QUERY_TEACHER: [
                "معلم", "استاذ", "دكتور", "معلمين", "مدرس", "مدرسين", "مكتب",
                "ساعات مكتبيه", "مقابله", "تواصل المعلم", "ايميل استاذ", "رئيس قسم",
                "قسم الرياضيات", "قسم اللغات", "قسم الحاسوب", "من يدرس", "مين يدرس",
                "من معلم", "معلم ماده"
            ],
            Intent.QUERY_CURRICULUM: [
                "منهج", "مناهج", "كتاب", "كتب", "مقرر", "مقررات", "وحده دراسيه",
                "دروس", "مواضيع", "فهرس الكتاب", "المقرر الدراسي"
            ],
            Intent.QUERY_EXAMS: [
                "اختبار", "اختبارات", "امتحان", "امتحانات", "ميدترم", "فاينل",
                "اختبار نصفي", "اختبار نهائي", "جدول الاختبارات", "موعد الامتحان"
            ],
            Intent.QUERY_CALENDAR: [
                "تقويم", "اجازه", "عطله", "عيد", "اجازات", "عطلات", "اجازه العيد",
                "عطله الربيع", "بدايه الفصل", "نهايه الفصل", "العام الدراسي", "الترم"
            ],
            Intent.QUERY_ACTIVITIES: [
                "نادي", "نوادي", "انديه", "رحله", "رحلات", "نادي الروبوت",
                "نادي الذكاء الاصطناعي", "نادي الخطابه", "نشاط", "انشطه", "معرض العلوم"
            ],
            Intent.QUERY_COMPETITIONS: [
                "مسابقه", "مسابقات", "اولمبياد", "جوائز", "منافسه", "تحدي القراءه",
                "اولمبياد البرمجه", "مسابقه القران"
            ],
            Intent.QUERY_ATTENDANCE: [
                "غياب", "تاخير", "حضور", "عذر", "طبي", "تقرير طبي",
                "عذر طبي", "انذار غياب", "حرمان", "نسبه الغياب", "ايام الغياب",
                "كم يوم اقدر اغيب", "خصم درجات الغياب"
            ],
            Intent.QUERY_GRADING: [
                "درجات", "توزيع الدرجات", "اعمال السنه", "الامتحان النهائي", "الدرجه الكليه",
                "رسوب", "دور ثاني", "اعاده اختبار", "لوحه الشرف", "لوحه", "الشرف", "شرف",
                "تكريم", "اوائل", "المتفوقين", "تفوق", "نسبه النجاح", "الحد الادني للنجاح", "المعدل"
            ],
            Intent.QUERY_DISCIPLINE: [
                "مخالفه", "عقوبه", "سلوك", "لائحه السلوك", "هروب", "هرب",
                "فصل", "تعهد", "مشاجره", "تنمر", "زي مدرسي", "مخالفه الزي",
                "عقوبات", "انضباط"
            ],
            Intent.QUERY_ADMISSION: [
                "قبول", "تسجيل", "شروط القبول", "اوراق التسجيل", "مستندات",
                "ملف الطالب", "تحويل", "رسوم", "شروط التسجيل", "طالب جديد",
                "كيف اسجل", "تقديم", "شروط التسجيل", "اسجل", "سجل", "التحاق",
                "اوراق", "وثائق", "متطلبات التسجيل"
            ],
            Intent.QUERY_FACILITIES: [
                "مكتبه", "معمل", "مختبر", "عياده", "مسرح", "صاله رياضيه",
                "ملعب", "مرافق", "غرفه التمريض", "معمل الحاسوب", "مختبر الفيزياء"
            ]
        }

        # 2. خرائط استخراج الأيام
        self.days_map = {
            "احد": "Sunday", "الاحد": "Sunday",
            "اثنين": "Monday", "الاثنين": "Monday",
            "ثلاثاء": "Tuesday", "الثلاثاء": "Tuesday",
            "اربعاء": "Wednesday", "الاربعاء": "Wednesday",
            "خميس": "Thursday", "الخميس": "Thursday"
        }

        # 3. خرائط الصفوف والمراحل
        self.grades_map = {
            "عاشر": "GRADE_10", "الاول ثانوي": "GRADE_10", "اول ثانوي": "GRADE_10", "صف 10": "GRADE_10", "10": "GRADE_10",
            "حادي عشر": "GRADE_11", "الثاني ثانوي": "GRADE_11", "ثاني ثانوي": "GRADE_11", "صف 11": "GRADE_11", "11": "GRADE_11",
            "ثاني عشر": "GRADE_12", "الثالث ثانوي": "GRADE_12", "ثالث ثانوي": "GRADE_12", "صف 12": "GRADE_12", "توجيهي": "GRADE_12", "12": "GRADE_12"
        }

        # 4. خرائط الحصص
        self.periods_map = {
            "اولي": "P_01", "الاولي": "P_01", "حصه 1": "P_01", "الحصه الاولي": "P_01",
            "ثانيه": "P_02", "الثانيه": "P_02", "حصه 2": "P_02", "الحصه الثانيه": "P_02",
            "ثالثه": "P_03", "الثالثه": "P_03", "حصه 3": "P_03", "الحصه الثالثه": "P_03",
            "رابعه": "P_04", "الرابعه": "P_04", "حصه 4": "P_04", "الحصه الرابعه": "P_04",
            "خامسه": "P_05", "الخامسه": "P_05", "حصه 5": "P_05", "الحصه الخامسه": "P_05",
            "سادسه": "P_06", "السادسه": "P_06", "حصه 6": "P_06", "الحصه السادسه": "P_06",
            "طابور": "P_ASSEMBLY", "الفسحه": "P_RECESS"
        }

        # 5. قائمة المواد للبحث الضبابي
        self.known_subjects = [
            "رياضيات", "فيزياء", "كيمياء", "احياء", "لغة عربية", "عربي", "نحو",
            "لغة انجليزية", "انجليزي", "حاسب الي", "حاسب", "ذكاء اصطناعي", "برمجة",
            "تربية اسلامية", "اسلامية", "قران", "تفاضل وتكامل"
        ]

        # 6. أسماء المعلمين ومفاتيحهم
        self.teacher_profiles = [
            {"id": "T_101", "clean_name": "أحمد محمود العلي", "first_names": ["احمد"], "aliases": ["احمد العلي", "احمد محمود", "استاذ احمد", "أحمد العلي"]},
            {"id": "T_102", "clean_name": "خالد عبد الرحمن السعيد", "first_names": ["خالد"], "aliases": ["خالد السعيد", "استاذ خالد", "خالد عبدالرحمن", "خالد عبد الرحمن"]},
            {"id": "T_103", "clean_name": "سارة إبراهيم الشمري", "first_names": ["سارة", "ساره"], "aliases": ["ساره الشمري", "سارة الشمري", "دكتوره ساره", "سارة ابراهيم", "ساره ابراهيم"]},
            {"id": "T_104", "clean_name": "معاذ عبدالله", "first_names": ["معاذ"], "aliases": ["معاذ عبدالله", "استاذ معاذ", "معاذ عبد الله"]}
        ]

        # 7. المرافق
        self.known_facilities = [
            "المكتبة المركزية", "مكتبة", "مختبر الفيزياء", "معمل الحاسوب",
            "العيادة المدرسية", "عيادة", "الصالة الرياضية", "المسرح المدرسي", "الملعب"
        ]

    def process_query(self, normalized_text: str) -> NLPResult:
        """
        المسار الرئيسي: يأخذ النص الموحد ويرجع النية والكيانات والدرجة الدقيقة للثقة.
        """
        if not normalized_text:
            return NLPResult(intent=Intent.UNKNOWN.value, confidence=0.0)

        intent, intent_score = self._classify_intent(normalized_text)
        entities = self._extract_entities(normalized_text)

        # حساب الثقة الواقعية
        confidence = self._calculate_confidence(intent, intent_score, entities)

        return NLPResult(
            intent=intent.value,
            entities=entities,
            confidence=round(confidence, 2)
        )

    def _strip_al_prefix(self, word: str) -> str:
        """إزالة ال التعريف إذا كانت الكلمة أطول من 3 أحرف"""
        if word.startswith("ال") and len(word) > 3:
            return word[2:]
        return word

    def _classify_intent(self, text: str) -> Tuple[Intent, float]:
        """
        يصنف نية المستخدم بذكاء بالاعتماد على حدود الكلمات وتجريد ال التعريف.
        """
        raw_words = text.split()
        unprefixed_words = [self._strip_al_prefix(w) for w in raw_words]
        combined_words = set(raw_words + unprefixed_words)

        best_intent = Intent.UNKNOWN
        best_score = 0.0

        for intent, keywords in self.intent_keywords.items():
            score = 0.0
            for kw in keywords:
                # 1. إذا كانت عبارة متعددة الكلمات
                if " " in kw:
                    if re.search(rf"\b{re.escape(kw)}\b", text):
                        score += 2.5
                else:
                    # 2. كلمة واحدة: مطابقة تامة مع حدود الكلمات
                    kw_unprefixed = self._strip_al_prefix(kw)
                    if kw in combined_words or kw_unprefixed in combined_words:
                        score += 1.2
                    elif re.search(rf"\b{re.escape(kw)}\b", text):
                        score += 1.0
                    else:
                        # 3. مطابقة تقريبية عالية الدقة
                        for w in combined_words:
                            if len(w) >= 4 and len(kw_unprefixed) >= 4:
                                ratio = fuzz.ratio(kw_unprefixed, w)
                                if ratio >= 90:
                                    score += 0.8
                                    break

            if score > best_score:
                best_score = score
                best_intent = intent

        if best_score < 0.8:
            return Intent.UNKNOWN, 0.0

        return best_intent, best_score

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """
        يستخرج كافة الكيانات المنطقية المرتبطة بالمدرسة بأمان ودقة.
        """
        entities: Dict[str, Any] = {}

        # 1. استخراج اليوم
        for ar_day, en_day in self.days_map.items():
            if re.search(rf"\b{ar_day}\b", text):
                entities["day"] = en_day
                break

        # 2. استخراج الصف / المرحلة
        for ar_grade, grade_id in self.grades_map.items():
            if ar_grade in text:
                entities["grade_id"] = grade_id
                break

        # 3. استخراج الحصة
        for ar_period, period_id in self.periods_map.items():
            if ar_period in text:
                entities["period_id"] = period_id
                break

        # 4. استخراج الشعبة
        class_match = re.search(r'\b(\d)\s*/\s*([ا-ي\d])\b', text)
        if class_match:
            entities["class_raw"] = f"{class_match.group(1)}/{class_match.group(2)}"
        else:
            sec_match = re.search(r'شعبه\s*([أاب-ي1-9])', text)
            if sec_match:
                entities["class_raw"] = sec_match.group(1)

        # 5. استخراج المادة الدراسية
        matched_subj = process.extractOne(
            text,
            self.known_subjects,
            scorer=fuzz.partial_token_set_ratio,
            score_cutoff=82
        )
        if matched_subj:
            entities["subject"] = matched_subj[0]

        # 6. استخراج اسم المعلم بأمان (يمنع التطابق الخاطئ مع عبارات عامة)
        for teacher in self.teacher_profiles:
            # التحقق من وجود الاسم الأول للمعلم أولاً في النص
            has_first_name = any(re.search(rf"\b{fn}\b", text) for fn in teacher["first_names"])
            if has_first_name:
                # فحص الألقاب والأسماء الكاملة
                for alias in teacher["aliases"]:
                    if alias in text or fuzz.token_set_ratio(alias, text) >= 85:
                        entities["teacher_name"] = teacher["clean_name"]
                        entities["teacher_id"] = teacher["id"]
                        break
                if "teacher_name" in entities:
                    break

        # 7. استخراج المرفق
        matched_fac = process.extractOne(
            text,
            self.known_facilities,
            scorer=fuzz.partial_token_set_ratio,
            score_cutoff=82
        )
        if matched_fac:
            entities["facility"] = matched_fac[0]

        return entities

    def _calculate_confidence(self, intent: Intent, intent_score: float, entities: Dict[str, Any]) -> float:
        """
        حساب نسبة الثقة بناءً على درجة مطابقة النية وعدد الكيانات المستخرجة.
        """
        if intent == Intent.UNKNOWN:
            return 0.15

        base = min(0.6 + (intent_score * 0.12), 0.90)
        # رفع الثقة إذا تم استخراج كيانات تؤكد المعنى
        if entities:
            base = min(base + len(entities) * 0.05, 0.98)

        return base


if __name__ == "__main__":
    from arabic_normalizer import ArabicNormalizer

    normalizer = ArabicNormalizer()
    nlp = NLPProcessor()

    test_queries = [
        "السلام عليكم ورحمة الله",
        "وين تقع مدرسة الرواد ورقم التواصل؟",
        "متي حصه الرياظيات للصف الثالث الثانوي يوم الاحد؟",
        "مين هو معلم الفيزياء لثالث ثانوي؟",
        "ايش هي كتب الصف العاشر؟",
        "متى تبدا اجازه عيد الفطر؟",
        "ايش عقوبة الهروب من المدرسة؟",
        "كم نسبة توزيع درجات النهائي؟",
        "ابغى اسجل ولدي في المدرسة ايش الشروط؟",
        "وين معمل الحاسوب؟"
    ]

    print("--- اختبار محرك NLP الموسع ---")
    for q in test_queries:
        norm_q = normalizer.normalize(q)
        res = nlp.process_query(norm_q)
        print(f"السؤال : {q}")
        print(f"النية  : {res.intent} (الثقة: {res.confidence})")
        print(f"الكيانات: {res.entities}")
        print("-" * 50)