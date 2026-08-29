from typing import Dict, Any, List

class ResponseGenerator:
    """
    وحدة توليد الردود (Response Generator).
    تأخذ نتائج محرك الاستدلال وتحولها إلى ردود بشرية طبيعية ومنسقة باللغة العربية.
    """

    def __init__(self):
        # خريطة عكسية لترجمة الأيام إلى العربية لعرضها للمستخدم
        self.days_ar_map = {
            "Sunday": "الأحد",
            "Monday": "الإثنين",
            "Tuesday": "الثلاثاء",
            "Wednesday": "الأربعاء",
            "Thursday": "الخميس"
        }

    def generate_response(self, intent, inference_result, entities=None):
        """توليد الرد النهائي بناءً على نتائج الاستدلال والنية"""
        
        # إذا كانت نتيجة الاستدلال نصاً مباشراً، نقوم بإرجاعها أو استخدامها كإجابة جاهزة
        if isinstance(inference_result, str):
            return inference_result
            
        # إذا كانت نتيجة الاستدلال على شكل قاموس (Dictionary)
        if isinstance(inference_result, dict):
            if inference_result.get("status") != "success":
                return inference_result.get("response", "عذراً، لم أتمكن من معالجة طلبك.")
            return inference_result.get("response", "")
            
        # إذا كانت كائناً (Object)
        if hasattr(inference_result, 'status') and inference_result.status != "success":
            return getattr(inference_result, 'response', "عذراً، حدث خطأ أثناء جلب البيانات.")
            
        return str(inference_result)
    def _format_error_response(self, error_message: str) -> str:
        """تنسيق رسائل الأخطاء بشكل ودي ولبق."""
        return f"عذراً، {error_message} 💡 يرجى التأكد من كتابة الصف واليوم بشكل واضح."

    def _format_schedule_response(self, schedule_data: List[Dict[str, Any]], entities: Dict[str, Any]) -> str:
        """
        تنسيق الجدول الدراسي على شكل قائمة نقطية (Markdown) جذابة وسهلة القراءة.
        """
        # محاولة استرجاع اسم اليوم بالعربية، أو استخدام قيمة افتراضية
        day_en = entities.get("day", "")
        day_ar = self.days_ar_map.get(day_en, "المحدد")
        
        class_raw = entities.get("class_raw", "غير محدد")
        
        # مقدمة الرد
        response_lines = [
            f"📅 **إليك الجدول الدراسي ليوم {day_ar} (شعبة {class_raw}):**\n"
        ]

        # بناء سطور الجدول بأسلوب القائمة النقطية
        for item in schedule_data:
            period_id = item.get("period_id", "").replace("P_", "")
            subject = item.get("subject", "غير محدد")
            teacher = item.get("teacher", "غير محدد")
            location = item.get("location_id", "")

            # تنسيق السطر لكل حصة
            line = f"* **الحصة {period_id}:** مادة {subject} | 👨‍🏫 أ. {teacher}"
            if location and location != "غير محدد":
                line += f" | 📍 ({location})"
            
            response_lines.append(line)

        # تذييل الرد (رسالة تشجيعية بسيطة)
        response_lines.append("\n💡 *أتمنى لك يوماً دراسياً موفقاً ومليئاً بالنجاح!*")

        # دمج السطور وإعادتها كنص واحد
        return "\n".join(response_lines)


# ==========================================
# اختبار محاكاة (Quick Test)
# ==========================================
if __name__ == "__main__":
    from dataclasses import dataclass
    
    # محاكاة كائن النتيجة القادم من InferenceEngine
    @dataclass
    class MockInferenceResult:
        status: str
        data: List[Dict[str, Any]]
        message: str

    mock_data = [
        {"period_id": "P_01", "subject": "الرياضيات", "teacher": "أحمد محمود", "location_id": "LOC_CLASS_3"},
        {"period_id": "P_02", "subject": "الفيزياء", "teacher": "سالم عبدالله", "location_id": "LOC_LAB_1"},
    ]
    
    mock_result = MockInferenceResult(status="success", data=mock_data, message="")
    mock_entities = {"day": "Sunday", "class_raw": "1"}

    generator = ResponseGenerator()
    final_text = generator.generate_response("query_schedule", mock_result, mock_entities)
    
    print("--- نتيجة الرد النهائي الموجه للمستخدم ---")
    print(final_text)