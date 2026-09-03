from typing import Dict, Any, List, Optional, Union


class ResponseGenerator:
    """
    وحدة توليد وتنسيق الردود النهائية (Response Generator).
    - تستقبل نتائج محرك الاستدلال (QueryResult، Dict، أو نص خام).
    - تنظم النصوص وتضمن التنسيق الجمالي باللغة العربية مع الرموز التعبيرية (Emojis).
    """

    def __init__(self):
        self.days_ar_map = {
            "Sunday": "الأحد",
            "Monday": "الإثنين",
            "Tuesday": "الثلاثاء",
            "Wednesday": "الأربعاء",
            "Thursday": "الخميس"
        }

    def generate_response(self, intent: str, inference_result: Any, entities: Optional[Dict[str, Any]] = None) -> str:
        """
        توليد الرد النهائي المنسق بناءً على نتيجة الاستدلال.
        """
        entities = entities or {}

        # 1. إذا كانت النتيجة نصاً مباشراً
        if isinstance(inference_result, str):
            return inference_result.strip()

        # 2. إذا كانت كائناً يحتوي على الخاصية response أو answer (مثل QueryResult)
        if hasattr(inference_result, 'response'):
            return getattr(inference_result, 'response', '').strip()

        if hasattr(inference_result, 'answer'):
            return getattr(inference_result, 'answer', '').strip()

        # 3. إذا كانت النتيجة قاموساً (Dictionary)
        if isinstance(inference_result, dict):
            if "response" in inference_result:
                return str(inference_result["response"]).strip()
            if "data" in inference_result and isinstance(inference_result["data"], list):
                if intent == "query_schedule":
                    return self._format_schedule_response(inference_result["data"], entities)

        return str(inference_result).strip()

    def _format_schedule_response(self, schedule_data: List[Dict[str, Any]], entities: Dict[str, Any]) -> str:
        """
        تنسيق الجدول الدراسي على شكل قائمة نقطية جذابة.
        """
        day_en = entities.get("day", "")
        day_ar = self.days_ar_map.get(day_en, "المحدد")
        class_raw = entities.get("class_raw", "العامة")

        response_lines = [
            f"📅 **إليك الجدول الدراسي ليوم {day_ar} (شعبة {class_raw}):**\n"
        ]

        for item in schedule_data:
            period_id = str(item.get("period_id", "")).replace("P_", "")
            subject = item.get("subject", "غير محدد")
            teacher = item.get("teacher", "غير محدد")
            location = item.get("location_name", item.get("location_id", ""))

            line = f"• **الحصة {period_id}:** مادة {subject} | 👨‍🏫 {teacher}"
            if location and location != "غير محدد":
                line += f" (📍 {location})"
            response_lines.append(line)

        response_lines.append("\n💡 *نتمنى لك يوماً دراسياً ممتعاً ومليئاً بالتوفيق!*")
        return "\n".join(response_lines)


if __name__ == "__main__":
    generator = ResponseGenerator()
    print("ResponseGenerator جاهز للاستخدام بنجاح.")


    