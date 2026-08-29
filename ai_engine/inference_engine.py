import os
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List

class InferenceEngine:
    def __init__(self, knowledge_base_path: Optional[str] = None, kb_path: Optional[str] = None, **kwargs: Any) -> None:
        """دالة التهيئة مع دعم مرن لمسار مجلد fact وقواعد المعرفة الشاملة"""
        path_arg = knowledge_base_path or kb_path

        base_dir = Path(__file__).resolve().parent
        project_root = base_dir.parent

        possible_kb_paths = [
            Path(path_arg) if path_arg else None,
            project_root / 'knowledge_base' / 'fact',
            project_root / 'knowledge_base',
            base_dir / 'knowledge_base' / 'fact',
            base_dir / 'knowledge_base',
            Path.cwd() / 'knowledge_base' / 'fact',
            Path.cwd() / 'knowledge_base',
        ]

        self.kb_path: Optional[Path] = None
        for p in possible_kb_paths:
            if p and p.exists() and p.is_dir():
                self.kb_path = p
                break

        if not self.kb_path:
            self.kb_path = project_root / 'knowledge_base' / 'fact'

        # تحميل كافة ملفات قاعدة المعرفة بدقة
        self.timetable_data = self._load_json_file('schedules_timetable.json')
        self.calendar_data = self._load_json_file('academic_calendar.json')
        self.activities_data = self._load_json_file('school_activities.json')
        self.curriculum_data = self._load_json_file('curriculum_books.json')
        self.grading_rules_data = self._load_json_file('grading_rules.json')
        self.evaluation_policy_data = self._load_json_file('evaluation_policy.json')
        self.attendance_policy_data = self._load_json_file('attendance_policy.json')
        self.admission_policy_data = self._load_json_file('admission_policy.json')

    def _load_json_file(self, target_filename: str) -> Any:
        """تحميل ملفات JSON مع البحث الشجري المتقدم"""
        possible_files = [
            self.kb_path / target_filename if self.kb_path else None,
            Path(__file__).resolve().parent.parent / 'knowledge_base' / 'fact' / target_filename,
            Path(__file__).resolve().parent.parent / 'knowledge_base' / target_filename,
            Path.cwd() / 'knowledge_base' / 'fact' / target_filename,
            Path.cwd() / 'knowledge_base' / target_filename,
            Path.cwd() / target_filename
        ]

        target_file = None
        for file_path in possible_files:
            if file_path and file_path.exists():
                target_file = file_path
                break

        if not target_file:
            search_roots = [Path.cwd(), Path(__file__).resolve().parent.parent]
            for root in search_roots:
                if root.exists():
                    matches = list(root.rglob(target_filename))
                    if matches:
                        target_file = matches[0]
                        break

        if target_file and target_file.exists():
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"ERROR: Error loading JSON from {target_file}: {e}")
        return {}

    def execute_query(self, user_query: str = "", intent: Optional[str] = None, entities: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
        return self.process_query(user_query=user_query, intent=intent, entities=entities, **kwargs)

    def process_query(self, user_query: str = "", intent: Optional[str] = None, entities: Optional[Dict[str, Any]] = None, **kwargs: Any) -> str:
        """المحرك الرئيسي المحدث: يوجه الاستعلام بدقة تامة دون تداخل أو تخمين عشوائي"""
        query = (user_query or "").strip()

        # 0. التوجيه المباشر بناءً على الـ Intent الصريح أو الكلمات المفتاحية
        if intent == 'query_rules_policy' or any(w in query for w in ['مخالفة', 'عقوبة', 'هربت', 'الهروب', 'تأخير طابور', 'تعهد', 'فصل', 'لائحة السلوك']):
            res = self._handle_grading_rules(query)
            if res: return res

        if intent == 'query_evaluation_policy' or any(w in query for w in ['درجات', 'أعمال السنة', 'النهائي', 'رسبت', 'رسوب', 'دور ثاني', 'لوحة الشرف', 'مرتبة الشرف']):
            res = self._handle_evaluation_policy(query)
            if res: return res

        if intent == 'query_attendance_policy' or any(w in query for w in ['غياب', 'عذر طبي', 'تقرير طبي', 'إنذار غياب']):
            res = self._handle_attendance_policy(query)
            if res: return res

        if intent == 'query_admission_policy' or any(w in query for w in ['تسجيل', 'قبول', 'طالب جديد', 'تحويل مدرسة', 'شروط القبول', 'أوراق']):
            res = self._handle_admission_policy(query)
            if res: return res

        if intent == 'query_curriculum' or any(w in query for w in ['كتاب', 'منهج', 'مادة', 'وحدة', 'سلسلة', 'أساسيات', 'الفيزياء المتقدمة']):
            res = self._handle_curriculum_query(query)
            if res: return res

        if intent == 'query_activities' or any(w in query for w in ['نادي', 'رحلة', 'مسابقة', 'أولمبياد', 'النشاط', 'معرض']):
            res = self._handle_activities_query(query)
            if res: return res

        if intent == 'query_events_calendar' or self._is_calendar_query(query):
            res = self._handle_calendar_query(query)
            if res: return res

        if intent == 'query_schedule' or any(w in query for w in ['جدول', 'حصص', 'الحصة', 'اليوم', 'أحد', 'اثنين', 'ثلاثاء', 'أربعاء', 'خميس']):
            res = self._process_timetable_query(query)
            if res: return res

        return self._smart_fallback_approximation(query)

    def _is_calendar_query(self, query: str) -> bool:
        calendar_keywords = ['إجازة', 'اجازة', 'عطلة', 'عيد', 'اليوم الوطني', 'منتصف العام', 'اختبار', 'اختبارات', 'ميد', 'نهائي', 'فعالية']
        return any(kw in query for kw in calendar_keywords)

    def _handle_calendar_query(self, query: str) -> Optional[str]:
        if not self.calendar_data: return None
        holidays = self.calendar_data.get('holidays_and_vacations', [])
        matched = []
        for h in holidays:
            title = h.get('title', '')
            if any(k in query for k in ['وطني', 'اليوم الوطني']) and 'وطني' in title: 
                matched.append(h)
            elif any(k in query for k in ['عيد', 'فطر']) and 'فطر' in title: 
                matched.append(h)
            elif any(k in query for k in ['منتصف العام', 'منتصف']) and 'منتصف' in title: 
                matched.append(h)
        
        if not matched: 
            matched = holidays

        res = ["🌴 **الإجازات والعطلات الرسمية:**\n"]
        for h in matched:
            res.append(f"• **{h.get('title')}**: من {h.get('start_date')} إلى {h.get('end_date')}")
        return "\n".join(res)

    def _handle_activities_query(self, query: str) -> Optional[str]:
        clubs = self.activities_data.get('student_clubs', [])
        trips = self.activities_data.get('school_trips', [])
        comps = self.activities_data.get('support_competitions', [])

        matched = []
        for c in clubs:
            if any(k in query for k in c.get('aliases', []) + [c.get('club_name')]):
                matched.append(f"🎯 **نادي مدرسي:** {c.get('club_name')} (الموعد: {c.get('meeting_schedule', {}).get('day')})")

        for t in trips:
            if any(k in query for k in t.get('aliases', []) + [t.get('title')]):
                matched.append(f"🚌 **رحلة مدرسية:** {t.get('title')} (التاريخ: {t.get('trip_date')})")

        for cp in comps:
            if any(k in query for k in cp.get('aliases', []) + [cp.get('title')]):
                matched.append(f"🏆 **مسابقة:** {cp.get('title')} (الموعد: {cp.get('competition_date')})")

        if matched: 
            return "\n".join(matched)
        if 'نشاط' in query or 'أنشطة' in query:
            return "📌 **تتوفر لدينا عدة أنشطة:** أندية تقنية وعلمية، رحلات ميدانية ترفيهية وعلمية، ومسابقات منهجية."
        return None

    def _handle_curriculum_query(self, query: str) -> Optional[str]:
        grades = self.curriculum_data.get('curriculum_and_books', [])
        
        for grade in grades:
            for sub in grade.get('curricula', []):
                if sub.get('subject_name') in query or any(alias in query for alias in sub.get('aliases', [])):
                    return (f"📖 **تفاصيل المقرر الدراسي:**\n"
                            f"• **المادة:** {sub.get('subject_name')}\n"
                            f"• **الصف:** {grade.get('grade_name')}\n"
                            f"• **الكتاب المعتمد:** {sub.get('approved_book')}")

        for grade in grades:
            g_name = grade.get('grade_name', '')
            if any(k in query for k in grade.get('aliases', []) + [g_name]):
                res = [f"📚 **مناهج وكتب {g_name}:**\n"]
                for sub in grade.get('curricula', []):
                    res.append(f"• **{sub.get('subject_name')}**: كتاب ({sub.get('approved_book')})")
                return "\n".join(res)
        return None

    def _handle_grading_rules(self, query: str) -> Optional[str]:
        levels = self.grading_rules_data.get('infraction_levels_and_penalties', [])
        for lvl in levels:
            if any(k in query for k in lvl.get('aliases', []) + [lvl.get('level_name'), lvl.get('description', '')]):
                res = [f"⚖️ **{lvl.get('level_name')}**: {lvl.get('description')}\n", "**الأمثلة المرتبطة:**"]
                for ex in lvl.get('examples', []): 
                    res.append(f"- {ex}")
                res.append("\n**الإجراءات والعقوبات المعتمدة:**")
                for p in lvl.get('penalties', []): 
                    res.append(f"- {p}")
                return "\n".join(res)
        
        if 'هربت' in query or 'هروب' in query:
            if len(levels) > 1:
                lvl = levels[1]
                return (f"⚠️ **التعامل مع حالة الهروب من الحصص:**\n"
                        f"تُصنف ضمن **{lvl.get('level_name')}**.\n"
                        f"**العقوبات المترتبة:**\n" + "\n".join([f"- {p}" for p in lvl.get('penalties', [])]))
        return None

    def _handle_evaluation_policy(self, query: str) -> Optional[str]:
        if any(w in query for w in ['درجات', 'أعمال السنة', 'النهائي', 'توزيع']):
            dist = self.evaluation_policy_data.get('grade_distribution', {})
            comp = dist.get('components', {})
            return (f"📊 **توزيع درجات المقرر الدراسي الواحد:**\n"
                    f"• أعمال السنة والمهام الأدائية: {comp.get('course_work', {}).get('weight_percentage', 0)}%\n"
                    f"• الاختبارات الشفهية والعملية: {comp.get('oral_and_practical', {}).get('weight_percentage', 0)}%\n"
                    f"• الاختبار التحريري النهائي: {comp.get('written_final', {}).get('weight_percentage', 0)}%\n"
                    f"*(الحد الأدنى العام للنجاح هو {dist.get('passing_threshold', 50)}%)*")
        
        if any(w in query for w in ['رسبت', 'رسوب', 'دور ثاني', 'إعادة']):
            retake = self.evaluation_policy_data.get('retake_rules', {})
            conditions = retake.get('conditions', [])
            res = ["🔄 **قواعد إعادة الاختبارات والرسوب:**\n"]
            for cond in conditions:
                res.append(f"• **الحالة:** {cond.get('case')}\n  **الإجراء:** {cond.get('action')}")
            return "\n".join(res)

        if any(w in query for w in ['شرف', 'تكريم', 'لوحة الشرف']):
            honor = self.evaluation_policy_data.get('honor_roll_conditions', {})
            crit = honor.get('criteria', {})
            return (f"🏆 **شروط مرتبة الشرف والتكريم:**\n"
                    f"• الحد الأدنى للمعدل: {crit.get('minimum_gpa_percentage', 0)}%\n"
                    f"• درجة السلوك: {crit.get('behavior_score_minimum', '')}\n"
                    f"• أقصى غياب بدون عذر: {crit.get('max_unexcused_absences', 0)} أيام\n"
                    f"• السجل السلوكي: {crit.get('disciplinary_record', '')}")
        return None

    def _handle_attendance_policy(self, query: str) -> Optional[str]:
        if 'غياب' in query or 'إنذار' in query:
            return ("📌 **لائحة الحضور والغياب:**\n"
                    "• **3 أيام غياب بدون عذر:** إرسال إنذار أول رسمي لولي الأمر ومراجعة المرشد الطلابي.\n"
                    "• **5 أيام غياب بدون عذر:** إرسال إنذار ثانٍ واستدعاء ولي الأمر لتوقيع تعهد خطي.\n"
                    "• **10 أيام غياب بدون عذر:** تحويل الملف إلى لجنة الانضباط واتخاذ إجراءات الحرمان.\n"
                    "• **الأعذار الطبية:** يجب تقديمها خلال 3 أيام عبر النظام المعتمد.")
        if 'عذر' in query or 'طبي' in query:
            med = self.attendance_policy_data.get('medical_excuses_procedure', {})
            return (f"🩺 **إجراءات الأعذار الطبية:**\n"
                    f"• المهلة الزمنية للتقديم: خلال {med.get('submission_timeframe_days', 3)} أيام.\n"
                    f"• المستندات المطلوبة:\n" + "\n".join([f"  - {doc}" for doc in med.get('required_documents', [])]))
        return None

    def _handle_admission_policy(self, query: str) -> Optional[str]:
        if any(w in query for w in ['تسجيل', 'قبول', 'طالب جديد']):
            adm = self.admission_policy_data.get('new_student_admission_requirements', {})
            reqs = adm.get('conditions', [])
            docs = adm.get('required_documents', [])
            return (f"📝 **شروط ومستندات قبول الطلاب المستجدين:**\n\n"
                    f"**الشروط:**\n" + "\n".join([f"• {r}" for r in reqs]) + "\n\n" +
                    f"**المستندات المطلوبة:**\n" + "\n".join([f"• {d}" for d in docs]))
        
        if 'تحويل' in query:
            trans = self.admission_policy_data.get('student_transfer_criteria', {})
            rules = trans.get('rules', [])
            res = ["🔄 **معايير الضوابط المنظمة للتحويل المدرسي:**\n"]
            for r in rules:
                res.append(f"• **{r.get('title')}**: {r.get('requirement')}")
            return "\n".join(res)
        return None

    def _process_timetable_query(self, query: str) -> Optional[str]:
        if not self.timetable_data: return None
        weekly_schedules = self.timetable_data.get('weekly_schedules', []) if isinstance(self.timetable_data, dict) else self.timetable_data
        if not weekly_schedules: return None

        day_map = {'الأحد': 'Sunday', 'الاحد': 'Sunday', 'الإثنين': 'Monday', 'الثلاثاء': 'Tuesday', 'الأربعاء': 'Wednesday', 'الخميس': 'Thursday'}
        target_day = next((en for ar, en in day_map.items() if ar in query), 'Sunday')

        target_grade = weekly_schedules[0]
        if any(w in query for w in ['الثالث', '12', 'ثالث']):
            target_grade = next((g for g in weekly_schedules if g.get('grade_id') == 'GRADE_12'), target_grade)
        elif any(w in query for w in ['الأول', '10', 'اول']):
            target_grade = next((g for g in weekly_schedules if g.get('grade_id') == 'GRADE_10'), target_grade)

        classes = target_grade.get('classes', [])
        if not classes: return None
        target_class = classes[0]
        for c in classes:
            if re.search(r'\bأ\b', query) and 'أ' in c.get('class_name', ''): 
                target_class = c; break
            elif re.search(r'\bب\b', query) and 'ب' in c.get('class_name', ''): 
                target_class = c; break

        schedule_dict = target_class.get('schedule', {})
        day_schedule = schedule_dict.get(target_day, [])
        if not day_schedule: return None

        subject_names_map = {
            'SUB_MATH_3': 'الرياضيات', 'SUB_PHY_3': 'الفيزياء', 'SUB_ARABIC_3': 'اللغة العربية',
            'SUB_CS_3': 'الحاسب الآلي', 'SUB_ISLAMIC_3': 'التربية الإسلامية', 'SUB_ENG_3': 'اللغة الإنجليزية'
        }

        response_lines = [f"📅 **جدول {target_grade.get('grade_name')} ({target_class.get('class_name')}):**\n"]
        for item in day_schedule:
            sub_id = item.get('subject_id', '')
            sub_name = subject_names_map.get(sub_id, sub_id)
            response_lines.append(f"• الحصة {item.get('period_id')}: {sub_name}")
        return "\n".join(response_lines)

    def _smart_fallback_approximation(self, query: str) -> str:
        return (f"🤖 **عذراً، لم أتمكن من مطابقة استفسارك بدقة:** \"{query}\"\n\n"
                f"يبدو أن السؤال خارج النطاق المباشر أو ناقص التفاصيل. يمكنك الاستفسار عن:\n"
                f"1. الجداول الدراسية (مثل: جدول ثالث ثانوي يوم الأحد).\n"
                f"2. الكتب والمناهج (مثل: كتاب الفيزياء المتقدمة لثالث ثانوي).\n"
                f"3. لوائح السلوك والانضباط (مثل: عقوبة الهروب من الحصص).\n"
                f"4. التقييم والدرجات (مثل: توزيع درجات أعمال السنة أو الرسوب).\n"
                f"5. شروط القبول والتسجيل والغياب.")