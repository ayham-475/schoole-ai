import os
import json
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union
from rapidfuzz import fuzz, process

from ai_engine.arabic_normalizer import ArabicNormalizer

# إعداد نظام التسجيل (Logging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """كائن موحد لنتائج الاستدلال"""
    response: str
    sources_used: List[str] = field(default_factory=list)
    confidence: float = 0.85
    status: str = "success"

    @property
    def answer(self) -> str:
        return self.response


class InferenceEngine:
    """
    محرك الاستدلال الذكي لنظام إدارة المدرسة (School Inference Engine).
    - يغطي كافة ملفات الحقائق (Facts) واللوائح (Rules) العشرة.
    - يدعم الربط العلائقي (Relational JOINs) بين المعلمين والأقسام والجداول والمواد.
    - يحتوي على بحث متعدد المستويات: توجيه مباشر بالنية -> بحث بالكلمات المفتاحية -> بحث ضبابي عميق.
    - يوفر الدالتين run_query و execute_query لتوافق تام مع كافة الواجهات.
    """

    DAY_MAP_AR_EN = {
        'الاحد': 'Sunday', 'أحد': 'Sunday', 'الأحد': 'Sunday', 'احد': 'Sunday',
        'الاثنين': 'Monday', 'إثنين': 'Monday', 'الإثنين': 'Monday', 'اثنين': 'Monday',
        'الثلاثاء': 'Tuesday', 'ثلاثاء': 'Tuesday',
        'الاربعاء': 'Wednesday', 'أربعاء': 'Wednesday', 'الأربعاء': 'Wednesday', 'اربعاء': 'Wednesday',
        'الخميس': 'Thursday', 'خميس': 'Thursday'
    }

    DAY_MAP_EN_AR = {
        'Sunday': 'الأحد',
        'Monday': 'الإثنين',
        'Tuesday': 'الثلاثاء',
        'Wednesday': 'الأربعاء',
        'Thursday': 'الخميس'
    }

    SOURCE_LABELS = {
        'school_profile.json': 'ملف المدرسة والخدمات والإدارة',
        'teachers_departments.json': 'سجلات المعلمين والأقسام الأكاديمية',
        'schedules_timetable.json': 'الجداول والحصص الدراسية',
        'curriculum_books.json': 'المناهج والمقررات والكتب الدراسية',
        'academic_calendar.json': 'التقويم الأكاديمي والإجازات والفعاليات',
        'facilities_activities.json': 'الأنشطة المدرسية والأندية والرحلات والمسابقات',
        'attendance_policies.json': 'لائحة وسياسات الحضور والغياب',
        'grading_rules.json': 'لائحة السلوك والانضباط المدرسي',
        'evaluation_policy.json': 'سياسات التقييم وتوزيع الدرجات',
        'admission_registration_rules.json': 'شروط القبول والتسجيل والتحويل'
    }

    def __init__(self, knowledge_base_path: Optional[Union[str, Path]] = None, kb_path: Optional[Union[str, Path]] = None, **kwargs: Any) -> None:
        self.normalizer = ArabicNormalizer()
        
        # تحديد المسارات الممكنة لقاعدة المعرفة
        path_arg = knowledge_base_path or kb_path
        base_dir = Path(__file__).resolve().parent
        project_root = base_dir.parent

        possible_dirs = [
            Path(path_arg) if path_arg else None,
            project_root / 'knowledge_base',
            base_dir / 'knowledge_base',
            Path.cwd() / 'knowledge_base'
        ]

        self.kb_root = next((p for p in possible_dirs if p and p.exists() and p.is_dir()), project_root / 'knowledge_base')
        logger.info(f"Using knowledge base root: {self.kb_root}")

        # تحميل كافة ملفات البيانات
        self.kb_data: Dict[str, Any] = {}
        self._load_all_kb_files()

        # بناء الفهارس العلائقية (Relational Indices)
        self.teachers_by_id: Dict[str, Dict[str, Any]] = {}
        self.departments_by_id: Dict[str, Dict[str, Any]] = {}
        self.periods_by_id: Dict[str, Dict[str, Any]] = {}
        self._build_indices()

    def _load_all_kb_files(self) -> None:
        """تحميل كافة ملفات JSON في مجلدي facts و rules"""
        json_filenames = [
            'school_profile.json',
            'teachers_departments.json',
            'schedules_timetable.json',
            'academic_calendar.json',
            'curriculum_books.json',
            'facilities_activities.json',
            'attendance_policies.json',
            'grading_rules.json',
            'evaluation_policy.json',
            'admission_registration_rules.json'
        ]

        for fname in json_filenames:
            self.kb_data[fname] = self._find_and_load_json(fname)

    def _find_and_load_json(self, target_filename: str) -> Any:
        """البحث عن ملف الـ JSON في facts أو rules أو كامل المشروع وتحميله"""
        candidates = [
            self.kb_root / 'facts' / target_filename,
            self.kb_root / 'rules' / target_filename,
            self.kb_root / target_filename
        ]

        target_file = next((c for c in candidates if c.exists()), None)

        if not target_file:
            # بحث أعمق
            for root in [self.kb_root, self.kb_root.parent]:
                if root.exists():
                    found = list(root.rglob(target_filename))
                    if found:
                        target_file = found[0]
                        break

        if target_file and target_file.exists():
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                logger.error(f"خطأ أثناء قراءة {target_file}: {e}")

        return {}

    def _build_indices(self) -> None:
        """بناء فهارس سريعة للربط العلائقي بين المعلمين والأقسام والحصص"""
        # 1. فهرس المعلمين
        td_data = self.kb_data.get('teachers_departments.json', {})
        for t in td_data.get('teachers', []):
            tid = t.get('teacher_id')
            if tid:
                self.teachers_by_id[tid] = t

        # 2. فهرس الأقسام
        for d in td_data.get('departments', []):
            did = d.get('department_id')
            if did:
                self.departments_by_id[did] = d

        # 3. فهرس الحصص ومواعيدها
        tt_data = self.kb_data.get('schedules_timetable.json', {})
        for p in tt_data.get('daily_periods', []):
            pid = p.get('period_id')
            if pid:
                self.periods_by_id[pid] = p

    # ---------------------------------------------------------
    # نقطة الدخول العامة (Public API)
    # ---------------------------------------------------------

    def run_query(self, user_query: str, intent: Optional[str] = None, entities: Optional[Dict[str, Any]] = None) -> QueryResult:
        """
        الواجهة العامة الموحدة لمعالجة الاستعلامات وإرجاع الرد الدقيق.
        """
        raw_query = user_query.strip()
        if not raw_query:
            return QueryResult(response="مرحباً بك! كيف يمكنني مساعدتك اليوم بخصوص مدرسة الرواد؟", confidence=1.0)

        entities = entities or {}
        norm_query = self.normalizer.normalize(raw_query)

        # 1. توجيه الاستعلام بناءً على النية الصريحة
        handler_map = {
            'greeting': self._handle_greeting,
            'school_info': self._handle_school_info,
            'query_schedule': self._handle_schedule,
            'query_teacher': self._handle_teacher,
            'query_curriculum': self._handle_curriculum,
            'query_events_calendar': self._handle_calendar,
            'query_exams': self._handle_exams,
            'query_activities': self._handle_activities,
            'query_competitions': self._handle_competitions,
            'query_attendance_policy': self._handle_attendance,
            'query_evaluation_policy': self._handle_grading,
            'query_rules_policy': self._handle_discipline,
            'query_admission_policy': self._handle_admission,
            'query_facilities': self._handle_facilities
        }

        # فحص المعالج المناسب للنية
        if intent and intent in handler_map:
            result = handler_map[intent](norm_query, entities)
            if result:
                return result

        # 2. فحص الكلمات المفتاحية المباشرة إذا لم تفلح النية
        routed_result = self._keyword_routing(norm_query, entities)
        if routed_result:
            return routed_result

        # 3. بحث ضبابي عميق في كافة ملفات قاعدة المعرفة
        deep_search_result = self._universal_deep_search(norm_query)
        if deep_search_result:
            return deep_search_result

        # 4. الرد الافتراضي الذكي
        return QueryResult(
            response=self._smart_fallback_approximation(raw_query),
            sources_used=[],
            confidence=0.2,
            status="fallback"
        )

    def execute_query(self, intent: Optional[str] = None, entities: Optional[Dict[str, Any]] = None, user_query: str = "") -> QueryResult:
        """دالة بديلة لضمان التوافق مع أي استدعاء قديم أو خارجي"""
        return self.run_query(user_query=user_query, intent=intent, entities=entities)

    # ---------------------------------------------------------
    # التوجيه بالكلمات المفتاحية
    # ---------------------------------------------------------

    def _keyword_routing(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        """توجيه ذكي بالاعتماد على الكلمات الصريحة في حال فشل تصنيف النية"""
        if any(w in norm_query for w in ['جدول', 'حصه', 'حصص']) or entities.get('day'):
            return self._handle_schedule(norm_query, entities)

        if any(w in norm_query for w in ['استاذ', 'معلم', 'مدرس', 'مكتب', 'ساعات مكتبيه']):
            return self._handle_teacher(norm_query, entities)

        if any(w in norm_query for w in ['كتاب', 'كتب', 'منهج', 'مقرر']):
            return self._handle_curriculum(norm_query, entities)

        if any(w in norm_query for w in ['اجازه', 'عطله', 'عيد', 'تقويم']):
            return self._handle_calendar(norm_query, entities)

        if any(w in norm_query for w in ['امتحان', 'امتحانات', 'اختبار', 'اختبارات']):
            return self._handle_exams(norm_query, entities)

        if any(w in norm_query for w in ['نادي', 'انديه', 'رحله', 'رحلات']):
            return self._handle_activities(norm_query, entities)

        if any(w in norm_query for w in ['مسابقه', 'مسابقات', 'اولمبياد']):
            return self._handle_competitions(norm_query, entities)

        if any(w in norm_query for w in ['غياب', 'عذر', 'طبي', 'انذار غياب']):
            return self._handle_attendance(norm_query, entities)

        if any(w in norm_query for w in ['درجات', 'توزيع الدرجات', 'رسوب', 'دور ثاني', 'لوحه الشرف']):
            return self._handle_grading(norm_query, entities)

        if any(w in norm_query for w in ['مخالفه', 'عقوبه', 'هروب', 'هرب', 'سلوك', 'فصل']):
            return self._handle_discipline(norm_query, entities)

        if any(w in norm_query for w in ['قبول', 'تسجيل', 'شروط القبول', 'تحويل', 'اوراق التسجيل']):
            return self._handle_admission(norm_query, entities)

        if any(w in norm_query for w in ['موقع', 'عنوان', 'رقم', 'هاتف', 'تواصل', 'مدير', 'دوام', 'باصات', 'مقصف']):
            return self._handle_school_info(norm_query, entities)

        if any(w in norm_query for w in ['مكتبه', 'معمل', 'مختبر', 'عياده', 'مسرح']):
            return self._handle_facilities(norm_query, entities)

        return None

    # ---------------------------------------------------------
    # المعالجات التخصصية (Specialized Handlers)
    # ---------------------------------------------------------

    def _handle_greeting(self, norm_query: str, entities: Dict[str, Any]) -> QueryResult:
        res = (
            "أهلاً وسهلاً بك في **مساعد مدرسة الرواد النموذجية الذكية**! 🎓\n\n"
            "أنا هنا لمساعدتك في كل ما يخص المدرسة، بما في ذلك:\n"
            "• 📅 **الجداول الدراسية** والحصص لجميع الصفوف.\n"
            "• 👨‍🏫 **بيانات المعلمين**، مكاتبهم، وساعاتهم المكتبية.\n"
            "• 📚 **المناهج والكتب المقررة**.\n"
            "• 🌴 **التقويم المدرسي** ومواعيد الإجازات والاختبارات.\n"
            "• ⚖️ **لوائح الحضور والغياب والانضباط والسلوك**.\n"
            "• 📝 **شروط القبول والتسجيل والتحويل**.\n"
            "• 🏢 **معلومات المدرسة ومرافقها ووسائل التواصل**.\n\n"
            "كيف يمكنني مساعدتك اليوم؟"
        )
        return QueryResult(response=res, sources_used=['school_profile.json'], confidence=0.95)

    def _handle_school_info(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('school_profile.json', {})
        if not data:
            return None

        overview = data.get('school_overview', {})
        contact = data.get('contact_info', {})
        admin_hours = data.get('administration_office_hours', [])
        services = data.get('student_services', {})
        features = data.get('school_features', {})

        # 1. أسئلة المدير أو الإدارة
        if any(w in norm_query for w in ['مدير', 'رئيس المدرسه', 'اداره']):
            principal = overview.get('principal', {})
            res = [
                f"👤 **{principal.get('role', 'مدير المدرسة')}:** {principal.get('title', '')} {principal.get('full_name', '')}",
                f"📍 **المكتب:** {principal.get('office_location', '')}\n"
            ]
            for admin in admin_hours:
                res.append(f"• **{admin.get('role')}:** {admin.get('title')} {admin.get('clean_name')} | 📍 {admin.get('office_location')} | ⏰ ساعات الاستقبال: {admin.get('reception_hours')}")
            return QueryResult(response="\n".join(res), sources_used=['school_profile.json'], confidence=0.92)

        # 2. وسائل الاتصال والعنوان
        if any(w in norm_query for w in ['رقم', 'هاتف', 'تلفون', 'تواصل', 'ايميل', 'عنوان', 'موقع', 'وين تقع', 'اين تقع']):
            phones = contact.get('phones', {})
            main_phone = phones.get('main', {}).get('number', '')
            affairs_phone = phones.get('student_affairs', {}).get('number', '')
            fin_phone = phones.get('financial', {}).get('number', '')

            res = (
                f"🏫 **بيانات التواصل والموقع - {overview.get('name', 'مدرسة الرواد')}:**\n\n"
                f"📍 **العنوان:** {contact.get('address', '')}\n"
                f"🗺️ **علامة مميزة:** {contact.get('google_maps_reference', '')}\n"
                f"📞 **الرقم الرئيسي / الاستقبال:** `{main_phone}`\n"
                f"📋 **شؤون الطلاب (القبول والغياب):** `{affairs_phone}`\n"
                f"💳 **الشؤون المالية والرسوم:** `{fin_phone}`\n"
                f"✉️ **البريد الإلكتروني:** `{contact.get('email', '')}`\n"
                f"🌐 **الموقع الإلكتروني:** {contact.get('website', '')}\n"
                f"⏰ **أوقات العمل:** {contact.get('working_days', '')} من الساعة {contact.get('working_hours', '')}"
            )
            return QueryResult(response=res, sources_used=['school_profile.json'], confidence=0.95)

        # 3. خدمات الطلاب (باصات، مقصف، إلخ)
        if any(w in norm_query for w in ['باص', 'باصات', 'مواصلات', 'مقصف', 'تغذيه']):
            res = (
                f"🚌 **خدمات النقل والتغذية:**\n\n"
                f"• **المواصلات:** {services.get('transportation', '')}\n"
                f"• **المقصف المدرسي:** {services.get('cafeteria', '')}"
            )
            return QueryResult(response=res, sources_used=['school_profile.json'], confidence=0.92)

        # 4. مميزات المدرسة والتعريف العام
        if any(w in norm_query for w in ['مميزات', 'عن المدرسه', 'نبذه', 'خصائص', 'رويه', 'رساله', 'من انتم']):
            features_list = features.get('features_list', [])
            res = [
                f"🏫 **{overview.get('name', 'مدرسة الرواد النموذجية الذكية')}**",
                f"• **النوع:** {overview.get('school_type', '')} (سنة التأسيس: {overview.get('established_year', '')})",
                f"• **الرؤية:** {overview.get('vision', '')}",
                f"• **الرسالة:** {overview.get('mission', '')}\n",
                "⭐ **أبرز المميزات:**"
            ]
            for feat in features_list[:4]:
                res.append(f"• **{feat.get('title')}:** {feat.get('description')}")
            return QueryResult(response="\n".join(res), sources_used=['school_profile.json'], confidence=0.90)

        # الرد الإجمالي العام للمدرسة
        res = (
            f"🏫 **{overview.get('name', 'مدرسة الرواد النموذجية الذكية')}**\n"
            f"📍 {contact.get('address', '')}\n"
            f"📞 للتواصل: `{contact.get('phones', {}).get('main', {}).get('number', '')}`\n"
            f"⏰ الدوام: {contact.get('working_days', '')} ({contact.get('working_hours', '')})"
        )
        return QueryResult(response=res, sources_used=['school_profile.json'], confidence=0.88)

    def _handle_schedule(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('schedules_timetable.json', {})
        weekly_schedules = data.get('weekly_schedules', [])
        if not weekly_schedules:
            return None

        # تحديد اليوم المستهدف
        target_day = entities.get('day')
        if not target_day:
            target_day = next((en for ar, en in self.DAY_MAP_AR_EN.items() if ar in norm_query), 'Sunday')

        day_name_ar = self.DAY_MAP_EN_AR.get(target_day, target_day)

        # تحديد الصف المستهدف
        target_grade_id = entities.get('grade_id')
        if not target_grade_id:
            if any(w in norm_query for w in ['ثالث', '12', 'ثاني عشر']):
                target_grade_id = 'GRADE_12'
            elif any(w in norm_query for w in ['اول', '10', 'عاشر']):
                target_grade_id = 'GRADE_10'
            elif any(w in norm_query for w in ['ثاني ثانوي', '11', 'حادي عشر']):
                target_grade_id = 'GRADE_11'
            else:
                target_grade_id = 'GRADE_12'  # الافتراضي

        # البحث عن الصف
        selected_grade = next((g for g in weekly_schedules if g.get('grade_id') == target_grade_id), weekly_schedules[0])
        classes = selected_grade.get('classes', [])
        if not classes:
            return None

        # تحديد الشعبة
        selected_class = classes[0]
        class_raw = entities.get('class_raw', '')
        if class_raw:
            for c in classes:
                if class_raw in c.get('class_name', '') or class_raw in c.get('class_id', ''):
                    selected_class = c
                    break

        day_schedule = selected_class.get('schedule', {}).get(target_day, [])
        if not day_schedule:
            # إذا لم يوجد جدول لهذا اليوم (مثل الجمعة أو السبت)
            return QueryResult(
                response=f"📅 لا توجد حصص مجدولة ليوم **{day_name_ar}** لصف **{selected_grade.get('grade_name')} ({selected_class.get('class_name')})**.",
                sources_used=['schedules_timetable.json'],
                confidence=0.85
            )

        # فحص ما إذا كان المستخدم يسأل عن حصة مادة معينة فقط
        target_subject = entities.get('subject')
        if target_subject:
            filtered_periods = []
            for item in day_schedule:
                sub_id = item.get('subject_id', '')
                # محاولة مطابقة اسم المادة
                if target_subject in sub_id or any(target_subject in s for s in [self._get_subject_name(sub_id)]):
                    filtered_periods.append(item)

            if filtered_periods:
                lines = [f"📅 **موعد حصة {target_subject} - يوم {day_name_ar}:**"]
                for p in filtered_periods:
                    period_info = self.periods_by_id.get(p.get('period_id'), {})
                    time_str = f"({period_info.get('start_time')} - {period_info.get('end_time')})" if period_info else ""
                    teacher_info = self._get_teacher_for_subject(p.get('subject_id'))
                    lines.append(f"• **الحصة {p.get('period_id', '').replace('P_', '')}:** {time_str} | 👨‍🏫 المعلم: {teacher_info}")
                return QueryResult(response="\n".join(lines), sources_used=['schedules_timetable.json', 'teachers_departments.json'], confidence=0.92)

        # بناء الجدول الكامل لليوم
        lines = [
            f"📅 **الجدول الدراسي ليوم {day_name_ar}**",
            f"🏫 **الصف:** {selected_grade.get('grade_name')} - شعبة ({selected_class.get('class_name')}):\n"
        ]

        for item in day_schedule:
            pid = item.get('period_id', '')
            sub_id = item.get('subject_id', '')
            sub_name = self._get_subject_name(sub_id)
            period_info = self.periods_by_id.get(pid, {})
            time_str = f"({period_info.get('start_time', '')} - {period_info.get('end_time', '')})" if period_info else ""
            teacher_name = self._get_teacher_for_subject(sub_id)

            lines.append(f"• **الحصة {pid.replace('P_', '')}:** {sub_name} {time_str} | 👨‍🏫 {teacher_name}")

        return QueryResult(response="\n".join(lines), sources_used=['schedules_timetable.json', 'teachers_departments.json'], confidence=0.90)

    def _get_subject_name(self, subject_id: str) -> str:
        """ترجمة رمز المادة إلى اسمها العربي"""
        subject_names = {
            'SUB_MATH_3': 'الرياضيات',
            'SUB_PHY_3': 'الفيزياء',
            'SUB_ARABIC_3': 'اللغة العربية',
            'SUB_CS_3': 'الحاسب الآلي والذكاء الاصطناعي',
            'SUB_ISLAMIC_3': 'التربية الإسلامية',
            'SUB_ENG_3': 'اللغة الإنجليزية',
            'SUB_CHEM_3': 'الكيمياء',
            'SUB_BIO_3': 'الأحياء',
            'SUB_MATH_1': 'الرياضيات',
            'SUB_SCI_1': 'العلوم العامة',
            'SUB_ARABIC_1': 'اللغة العربية'
        }
        return subject_names.get(subject_id, subject_id)

    def _get_teacher_for_subject(self, subject_id: str) -> str:
        """ربط علائقي (Relational JOIN): استخراج اسم المعلم بناءً على رمز المادة"""
        subject_to_teacher = {
            'SUB_MATH_3': 'T_101',
            'SUB_PHY_3': 'T_102',
            'SUB_ARABIC_3': 'T_103',
            'SUB_CS_3': 'T_104',
            'SUB_MATH_1': 'T_101'
        }
        tid = subject_to_teacher.get(subject_id)
        if tid and tid in self.teachers_by_id:
            return self.teachers_by_id[tid].get('clean_name', '')
        return "هيئة التدريس"

    def _handle_teacher(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        td_data = self.kb_data.get('teachers_departments.json', {})
        teachers = td_data.get('teachers', [])
        departments = td_data.get('departments', [])
        if not teachers:
            return None

        # 1. البحث بالمعلم المحدد
        target_teacher = None
        teacher_id = entities.get('teacher_id')
        if teacher_id and teacher_id in self.teachers_by_id:
            target_teacher = self.teachers_by_id[teacher_id]

        if not target_teacher:
            teacher_name = entities.get('teacher_name', '')
            for t in teachers:
                if teacher_name and (teacher_name in t.get('clean_name', '') or t.get('clean_name', '') in teacher_name):
                    target_teacher = t
                    break
                for kw in t.get('search_keywords', []):
                    if kw in norm_query:
                        target_teacher = t
                        break
                if target_teacher:
                    break

        # 2. إذا لم يُحدد بالاسم، فالبحث بالمادة (مثل: مين يدرس رياضيات أو فيزياء)
        if not target_teacher:
            subject = entities.get('subject', '')
            for t in teachers:
                for s in t.get('subjects_taught', []):
                    if subject and (subject in s or s in subject):
                        target_teacher = t
                        break
                    if any(w in norm_query for w in self.normalizer.extract_keywords(s)):
                        target_teacher = t
                        break
                if target_teacher:
                    break

        # إذا وجدنا معلماً محدداً: إرجاع ملفه بالكامل مع الساعات المكتبية
        if target_teacher:
            dep_id = target_teacher.get('department_id')
            dep_name = self.departments_by_id.get(dep_id, {}).get('department_name', '')
            
            hours_lines = []
            for h in target_teacher.get('available_meeting_hours', []):
                day_ar = self.DAY_MAP_EN_AR.get(h.get('day'), h.get('day'))
                hours_lines.append(f"  • يوم {day_ar}: من {h.get('start_time')} إلى {h.get('end_time')} (📍 {h.get('location_name')})")

            hours_str = "\n".join(hours_lines) if hours_lines else "  • بالتنسيق المسبق مع إدارة القسم."

            res = (
                f"👨‍🏫 **بيانات المعلم:**\n\n"
                f"• **الاسم:** {target_teacher.get('title')} {target_teacher.get('clean_name')}\n"
                f"• **القسم الأكاديمي:** {dep_name}\n"
                f"• **التخصص:** {target_teacher.get('specialization')}\n"
                f"• **المواد التي يدرسها:** {', '.join(target_teacher.get('subjects_taught', []))}\n"
                f"• **البريد الإلكتروني:** `{target_teacher.get('contact', {}).get('email', '')}`\n\n"
                f"⏰ **الساعات المكتبية والاستقبال:**\n{hours_str}"
            )
            return QueryResult(response=res, sources_used=['teachers_departments.json'], confidence=0.94)

        # 3. إذا كان السؤال عن الأقسام الأكاديمية
        if any(w in norm_query for w in ['اقسام', 'قسم']):
            lines = ["🏛️ **الأقسام الأكاديمية بمدرسة الرواد:**\n"]
            for d in departments:
                head_teacher = self.teachers_by_id.get(d.get('head_of_department_id'), {})
                lines.append(f"• **{d.get('department_name')}** | رئيس القسم: {head_teacher.get('title', '')} {head_teacher.get('clean_name', 'غير محدد')}")
            return QueryResult(response="\n".join(lines), sources_used=['teachers_departments.json'], confidence=0.90)

        # 4. عرض قائمة المعلمين العامة
        lines = ["👨‍🏫 **قائمة المعلمين المتاحين للاستفسار:**\n"]
        for t in teachers:
            lines.append(f"• **{t.get('title')} {t.get('clean_name')}** ({t.get('specialization')}) - المواد: {', '.join(t.get('subjects_taught', []))}")
        lines.append("\n💡 يمكنك السؤال باسم المعلم أو المادة لمعرفة مواعيد الاستقبال ومكتبه.")
        return QueryResult(response="\n".join(lines), sources_used=['teachers_departments.json'], confidence=0.88)

    def _handle_curriculum(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('curriculum_books.json', {})
        stages = data.get('educational_stages', [])
        if not stages:
            return None

        target_grade_id = entities.get('grade_id')
        target_subject = entities.get('subject')

        # 1. إذا سأل عن صف معين (مثل الصف العاشر أو الثالث ثانوي)
        if target_grade_id:
            for stage in stages:
                for grade in stage.get('grades', []):
                    if grade.get('grade_id') == target_grade_id:
                        lines = [f"📚 **المناهج والكتب المقررة لـ {grade.get('grade_name')} ({stage.get('stage_name')}):**\n"]
                        for b in grade.get('books', []):
                            subj = b.get('subject', b.get('subject_name', ''))
                            teacher = b.get('teacher_name', 'هيئة التدريس')
                            sem = b.get('semester', b.get('term', ''))
                            desc = b.get('description', '')
                            lines.append(f"• **{b.get('book_name')}** ({subj}) | 👨‍🏫 المعلم: {teacher} | 📅 {sem}\n  📝 {desc}")
                        return QueryResult(response="\n".join(lines), sources_used=['curriculum_books.json'], confidence=0.95)

        # 2. إذا سأل عن مادة معينة
        if target_subject:
            lines = [f"📖 **الكتب والمناهج الخاصة بمادة {target_subject}:**\n"]
            found = False
            for stage in stages:
                for grade in stage.get('grades', []):
                    for b in grade.get('books', []):
                        subj = b.get('subject', b.get('subject_name', ''))
                        book_n = b.get('book_name', '')
                        if target_subject in subj or target_subject in book_n:
                            found = True
                            teacher = b.get('teacher_name', 'هيئة التدريس')
                            lines.append(f"• **{book_n}** ({grade.get('grade_name')}) | 👨‍🏫 {teacher}\n  📝 {b.get('description', '')}")
            if found:
                return QueryResult(response="\n".join(lines), sources_used=['curriculum_books.json'], confidence=0.93)

        # 3. عرض المراحل الدراسية والخيارات
        lines = [
            "📚 **المناهج والكتب المدرسية:**\n",
            "تغطي مناهجنا كافة المراحل الدراسية:"
        ]
        for stage in stages:
            grade_names = [g.get('grade_name') for g in stage.get('grades', [])]
            lines.append(f"• **{stage.get('stage_name')}:** {', '.join(grade_names)}")
        lines.append("\n💡 لمعرفة الكتب، يرجى كتابة اسم الصف (مثال: *كتب الصف العاشر* أو *منهج الفيزياء*).")
        return QueryResult(response="\n".join(lines), sources_used=['curriculum_books.json'], confidence=0.85)

    def _handle_calendar(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('academic_calendar.json', {})
        holidays = data.get('holidays_and_vacations', [])
        terms = data.get('terms', [])
        deadlines = data.get('administrative_deadlines', [])

        # 1. الإجازات والعطلات
        if any(w in norm_query for w in ['اجازه', 'عطله', 'عيد', 'اجازات', 'عطلات']):
            lines = [f"🌴 **الإجازات والعطلات الرسمية للعام الدراسي {data.get('academic_year', '')}:**\n"]
            for h in holidays:
                lines.append(f"• **{h.get('title')}**: من `{h.get('start_date')}` إلى `{h.get('end_date')}` ({h.get('category')})")
            return QueryResult(response="\n".join(lines), sources_used=['academic_calendar.json'], confidence=0.95)

        # 2. الفصول الدراسية وبداية/نهاية الترم
        if any(w in norm_query for w in ['فصل', 'ترم', 'بدايه', 'نهايه', 'تقويم']):
            lines = [f"📅 **التقويم الأكاديمي للعام الدراسي {data.get('academic_year', '')}:**\n"]
            for t in terms:
                lines.append(f"• **{t.get('name')}**: من `{t.get('start_date')}` إلى `{t.get('end_date')}` (الحالة: {t.get('status')})")
            if deadlines:
                lines.append("\n📌 **مواعيد إدارية هامة:**")
                for d in deadlines:
                    lines.append(f"• {d.get('title')}: `{d.get('deadline_date')}`")
            return QueryResult(response="\n".join(lines), sources_used=['academic_calendar.json'], confidence=0.92)

        return self._handle_exams(norm_query, entities)

    def _handle_exams(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('academic_calendar.json', {})
        terms = data.get('terms', [])

        lines = ["📝 **مواعيد الاختبارات المدرسية:**\n"]
        has_exams = False
        for t in terms:
            milestones = t.get('key_milestones', [])
            for m in milestones:
                if 'اختبار' in m.get('title', '') or 'امتحان' in m.get('title', ''):
                    has_exams = True
                    lines.append(f"• **{m.get('title')} ({t.get('name')}):** من `{m.get('start_date')}` إلى `{m.get('end_date')}`")

        if has_exams:
            return QueryResult(response="\n".join(lines), sources_used=['academic_calendar.json'], confidence=0.92)

        return QueryResult(
            response="📝 تبدأ اختبارات منتصف الفصل الأول في منتصف أكتوبر، والاختبارات النهائية في ديسمبر. يرجى مراجعة إدارة شؤون الطلاب للحصول على جدول الاختبار التفصيلي.",
            sources_used=['academic_calendar.json'],
            confidence=0.80
        )

    def _handle_activities(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('facilities_activities.json', {})
        clubs = data.get('student_clubs', [])
        trips = data.get('school_trips', [])

        # 1. الرحلات
        if any(w in norm_query for w in ['رحله', 'رحلات']):
            lines = ["🚌 **الرحلات المدرسية المجدولة:**\n"]
            for t in trips:
                lines.append(
                    f"• **{t.get('title')}**\n"
                    f"  📅 التاريخ: `{t.get('trip_date')}` | آخر موعد للتسجيل: `{t.get('registration_deadline')}`\n"
                    f"  🎯 الأنشطة: {t.get('what_it_offers')}\n"
                    f"  👨‍🏫 المشرف: {t.get('supervisor_name')}"
                )
            return QueryResult(response="\n\n".join(lines), sources_used=['facilities_activities.json'], confidence=0.94)

        # 2. الأندية الطلابية
        lines = ["🎯 **الأندية والأنشطة الطلابية:**\n"]
        for c in clubs:
            sch = c.get('meeting_schedule', {})
            lines.append(
                f"• **{c.get('club_name')}**\n"
                f"  👨‍🏫 المشرف: {c.get('supervisor_name')} | 📍 {c.get('location')}\n"
                f"  ⏰ الموعد: يوم {sch.get('day')} ({sch.get('start_time')} - {sch.get('end_time')})\n"
                f"  💡 ما يقدمه: {c.get('what_it_offers')}"
            )
        return QueryResult(response="\n\n".join(lines), sources_used=['facilities_activities.json'], confidence=0.93)

    def _handle_competitions(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('facilities_activities.json', {})
        comps = data.get('support_competitions', [])
        if not comps:
            return None

        lines = ["🏆 **المسابقات والجوائز المدرسية:**\n"]
        for c in comps:
            lines.append(
                f"• **{c.get('title')}**\n"
                f"  🏢 الجهة المنظمة: {c.get('organizing_body')}\n"
                f"  📅 تاريخ المسابقة: `{c.get('competition_date')}` (آخر موعد للتسجيل: `{c.get('registration_deadline')}`)\n"
                f"  🎁 الجوائز والمزايا: {c.get('what_it_offers')}"
            )
        return QueryResult(response="\n\n".join(lines), sources_used=['facilities_activities.json'], confidence=0.94)

    def _handle_attendance(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('attendance_policies.json', {})
        policy_info = data.get('lateness_and_absence_conditions', {})
        medical = data.get('medical_excuses_procedure', {})
        absence_conds = policy_info.get('absence_conditions', [])
        lateness_rules = policy_info.get('lateness_rules', [])

        # 1. الأعذار الطبية
        if any(w in norm_query for w in ['عذر', 'طبي', 'مرض', 'تقرير']):
            docs = ", ".join(medical.get('required_documents', []))
            res = (
                f"🩺 **إجراءات تقديم الأعذار الطبية:**\n\n"
                f"• **مهلة التقديم:** خلال `{medical.get('submission_timeframe_days', 3)}` أيام عمل من تاريخ الغياب.\n"
                f"• **المستندات المطلوبة:** {docs}.\n"
                f"• **خطوات الاعتماد:** {medical.get('approval_workflow', 'مراجعة العيادة ثم اعتماد شؤون الطلاب')}."
            )
            return QueryResult(response=res, sources_used=['attendance_policies.json'], confidence=0.95)

        # 2. التأخير الصباحي
        if any(w in norm_query for w in ['تاخير', 'صباحي', 'طابور']):
            lines = ["⏰ **ضوابط وقواعد التأخر الصباحي:**\n"]
            for r in lateness_rules:
                lines.append(f"• **{r.get('condition')}:** {r.get('penalty_or_action')}")
            return QueryResult(response="\n".join(lines), sources_used=['attendance_policies.json'], confidence=0.92)

        # 3. لائحة الغياب والإنذارات
        lines = [
            "📋 **لائحة الحضور والغياب المعتمدة:**\n"
        ]
        for a in absence_conds:
            lines.append(f"• **{a.get('condition')}:** {a.get('penalty_or_action')}")
        lines.append(f"\n💡 للأعذار الطبية: مهلة التقديم `{medical.get('submission_timeframe_days', 3)}` أيام.")
        return QueryResult(response="\n".join(lines), sources_used=['attendance_policies.json'], confidence=0.93)

    def _handle_grading(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('evaluation_policy.json', {})
        dist = data.get('grade_distribution', {})
        retake = data.get('retake_rules', {})
        honor = data.get('honor_roll_conditions', {})

        # 1. لوحة الشرف والتكريم
        if any(w in norm_query for w in ['شرف', 'تكريم', 'اوائل', 'امتياز']):
            crit = honor.get('criteria', {})
            res = (
                f"🏆 **شروط الانضمام للوحة الشرف والتكريم:**\n\n"
                f"• **الحد الأدنى للمعدل:** لا يقل عن `{crit.get('minimum_gpa_percentage', 90)}%`.\n"
                f"• **تقييم السلوك:** ألا يقل عن `{crit.get('behavior_score_minimum', 'ممتاز')}`.\n"
                f"• **الرسوب:** {crit.get('no_failed_subjects_condition', 'عدم الرسوب في أي مادة')}."
            )
            return QueryResult(response=res, sources_used=['evaluation_policy.json'], confidence=0.94)

        # 2. إعادة الاختبار والدور الثاني والرسوب
        if any(w in norm_query for w in ['رسوب', 'دور ثاني', 'اعاده', 'ملحق']):
            lines = ["🔄 **قواعد وضوابط إعادة الاختبارات (الدور الثاني):**\n"]
            for c in retake.get('conditions', []):
                lines.append(f"• **{c.get('case')}:** {c.get('action')}")
            return QueryResult(response="\n".join(lines), sources_used=['evaluation_policy.json'], confidence=0.93)

        # 3. توزيع الدرجات
        components = dist.get('components', {})
        cw = components.get('course_work', {})
        wf = components.get('written_final', {})
        res = (
            f"📊 **سياسة تقييم وتوزيع الدرجات:**\n\n"
            f"• **أعمال السنة والاختبارات الدورية:** `{cw.get('weight_percentage', 50)}%` ({cw.get('description', '')})\n"
            f"• **الاختبار النهائي التحريري:** `{wf.get('weight_percentage', 50)}%` ({wf.get('description', '')})\n"
            f"• **الحد الأدنى للنجاح:** `{dist.get('passing_threshold', 50)}%` في المادة الواحدة.\n"
            f"📌 {dist.get('passing_note', '')}"
        )
        return QueryResult(response=res, sources_used=['evaluation_policy.json'], confidence=0.95)

    def _handle_discipline(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('grading_rules.json', {})
        levels = data.get('infraction_levels_and_penalties', [])
        if not levels:
            return None

        # 1. مخالفة محددة: الهروب من المدرسة
        if any(w in norm_query for w in ['هرب', 'هروب']):
            for lvl in levels:
                for ex in lvl.get('examples', []):
                    if 'هروب' in ex or 'خروج' in ex:
                        res = [
                            f"⚠️ **مخالفة الهروب من المدرسة ({lvl.get('level_name')}):**\n",
                            f"• **الوصف:** {lvl.get('description')}\n",
                            "**العقوبات والإجراءات المتخذة:**"
                        ]
                        for p in lvl.get('penalties', []):
                            res.append(f"- {p}")
                        return QueryResult(response="\n".join(res), sources_used=['grading_rules.json'], confidence=0.95)

        # 2. مخالفة الزي المدرسي
        if any(w in norm_query for w in ['زي', 'لباس', 'مظهر']):
            lvl = levels[0]  # المخالفات البسيطة
            res = [
                f"👔 **مخالفة عدم الالتزام بالزي المدرسي ({lvl.get('level_name')}):**\n",
                "**العقوبات المتدرجة:**"
            ]
            for p in lvl.get('penalties', []):
                res.append(f"- {p}")
            return QueryResult(response="\n".join(res), sources_used=['grading_rules.json'], confidence=0.92)

        # 3. عرض كافة درجات المخالفات
        lines = ["⚖️ **لائحة السلوك والانضباط المدرسي:**\n"]
        for lvl in levels:
            ex_str = "، ".join(lvl.get('examples', [])[:2])
            lines.append(
                f"• **{lvl.get('level_name')}**: {lvl.get('description')}\n"
                f"  أمثلة: {ex_str}\n"
                f"  أبرز العقوبات: {lvl.get('penalties', [''])[0]}"
            )
        lines.append("\n💡 يمكنك الاستفسار عن مخالفة بعينها لمعرفة تفاصيل العقوبة المقررة.")
        return QueryResult(response="\n".join(lines), sources_used=['grading_rules.json'], confidence=0.90)

    def _handle_admission(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        data = self.kb_data.get('admission_registration_rules.json', {})
        adm = data.get('new_student_admission_requirements', {})
        transfer = data.get('student_transfer_criteria', {})

        # 1. التحويل من مدرسة أخرى
        if any(w in norm_query for w in ['تحويل', 'نقل', 'محول']):
            lines = ["🔄 **ضوابط ومعايير تحويل الطلاب إلى مدرسة الرواد:**\n"]
            for r in transfer.get('rules', []):
                lines.append(f"• **{r.get('title')}:** {r.get('requirement')}")
            return QueryResult(response="\n".join(lines), sources_used=['admission_registration_rules.json'], confidence=0.94)

        # 2. شروط التسجيل والقبول للطلاب الجدد
        conds = adm.get('conditions', [])
        docs = adm.get('required_documents', [])

        lines = [
            "📝 **شروط وإجراءات تسجيل الطلاب الجدد:**\n",
            "**أولاً: شروط القبول:**"
        ]
        for c in conds:
            lines.append(f"• {c}")

        lines.append("\n**ثانياً: الوثائق والمستندات المطلوبة:**")
        for d in docs:
            lines.append(f"• {d}")

        lines.append("\n💡 لمزيد من التفاصيل، يرجى مراجعة قسم شؤون الطلاب أو الاتصال على الرقم: `+967-1-234568`.")
        return QueryResult(response="\n".join(lines), sources_used=['admission_registration_rules.json'], confidence=0.95)

    def _handle_facilities(self, norm_query: str, entities: Dict[str, Any]) -> Optional[QueryResult]:
        profile = self.kb_data.get('school_profile.json', {})
        facilities = profile.get('facilities', [])
        if not facilities:
            return None

        # البحث عن مرفق محدد
        target_fac = entities.get('facility')
        matched_f = None
        for f in facilities:
            fname = f.get('name', '')
            aliases = f.get('aliases', [])
            all_tokens = [fname] + aliases

            # مطابقة مباشرة أو بالكيانات
            if target_fac and any(target_fac in tok or tok in target_fac or fuzz.partial_ratio(target_fac, tok) >= 75 for tok in all_tokens):
                matched_f = f
                break
            if any(w in norm_query for w in aliases) or any(fuzz.partial_ratio(a, norm_query) >= 80 for a in aliases):
                matched_f = f
                break
            if any(w in norm_query for w in ['حاسوب', 'كمبيوتر', 'معمل', 'حاسب']) and any(k in fname for k in ['حاسوب', 'حاسب', 'ذكاء اصطناعي']):
                matched_f = f
                break
            if any(w in norm_query for w in ['عياده', 'طبيب', 'تمريض', 'دكتور']) and 'عيادة' in fname:
                matched_f = f
                break
            if any(w in norm_query for w in ['مكتبه', 'استعاره', 'قراءه']) and 'مكتبة' in fname:
                matched_f = f
                break

        if matched_f:
            res = (
                f"🏢 **مرفق: {matched_f.get('name')}**\n\n"
                f"📍 **الموقع:** {matched_f.get('location')}\n"
                f"⏰ **ساعات العمل:** {matched_f.get('operating_hours')}\n"
                f"👤 **المسؤول:** {matched_f.get('responsible_person')}\n"
                f"📌 **التفاصيل والقواعد:** {matched_f.get('details_and_rules')}"
            )
            return QueryResult(response=res, sources_used=['school_profile.json'], confidence=0.93)

        # عرض قائمة المرافق المتاحة
        lines = ["🏢 **المرافق المدرسية المتاحة:**\n"]
        for f in facilities:
            lines.append(f"• **{f.get('name')}**: 📍 {f.get('location')} (ساعات العمل: {f.get('operating_hours')})")
        return QueryResult(response="\n".join(lines), sources_used=['school_profile.json'], confidence=0.88)

    # ---------------------------------------------------------
    # البحث الضبابي والبديل الذكي
    # ---------------------------------------------------------

    def _universal_deep_search(self, norm_query: str) -> Optional[QueryResult]:
        """بحث عميق في كافة النصوص الحقيقية لاستخراج أدق إجابة ممكنة"""
        keywords = self.normalizer.extract_keywords(norm_query)
        if not keywords:
            return None

        candidates: List[Tuple[float, str, str]] = []

        def search_struct(val: Any, source_file: str, context: str = "") -> None:
            if isinstance(val, dict):
                for k, v in val.items():
                    if k.lower() in ['metadata', 'version', 'last_updated', 'description']:
                        continue
                    search_struct(v, source_file, k)
            elif isinstance(val, list):
                for item in val:
                    search_struct(item, source_file, context)
            elif isinstance(val, str) and len(val) > 10:
                norm_val = self.normalizer.normalize(val)
                # حساب درجة المطابقة
                matched_count = sum(1 for kw in keywords if kw in norm_val)
                if matched_count > 0:
                    score = (matched_count / len(keywords)) * 100
                    candidates.append((score, val, source_file))

        for fname, content in self.kb_data.items():
            search_struct(content, fname)

        if candidates:
            # فرز النتائج تنازلياً حسب درجة المطابقة
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_text, source_file = candidates[0]
            if best_score >= 40:
                source_label = self.SOURCE_LABELS.get(source_file, source_file)
                res = f"📌 {best_text}\n\n📁 **المصدر المعتمد:** `{source_label}`"
                return QueryResult(response=res, sources_used=[source_file], confidence=round(min(best_score / 100, 0.85), 2))

        return None

    def _smart_fallback_approximation(self, raw_query: str) -> str:
        """رسالة بديلة ذكية ولبقة عند عدم العثور على إجابة محددة"""
        return (
            f"🤖 **عذراً، لم أتمكن من العثور على إجابة دقيقة لاستفسارك:** *\"{raw_query}\"*\n\n"
            f"💡 **يمكنك تجربة إحدى الصيغ التالية:**\n"
            f"• 📅 *\"جدول ثالث ثانوي يوم الأحد\"* أو *\"متى حصة الرياضيات؟\"*\n"
            f"• 👨‍🏫 *\"من هو معلم الفيزياء؟\"* أو *\"أين مكتب أستاذ أحمد؟\"*\n"
            f"• 📚 *\"ما هي كتب الصف العاشر؟\"*\n"
            f"• 🌴 *\"متى إجازة العيد؟\"* أو *\"مواعيد الاختبارات\"*\n"
            f"• ⚖️ *\"عقوبة الهروب من المدرسة\"* أو *\"قوانين الغياب والأعذار الطبية\"*\n"
            f"• 📝 *\"شروط القبول والتسجيل\"* أو *\"رقم التواصل وموقع المدرسة\"*"
        )
