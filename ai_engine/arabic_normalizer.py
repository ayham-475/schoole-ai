import re
import string
from typing import Dict


class ArabicNormalizer:
    """
    وحدة معالجة وتوحيد النص العربي عالية الأداء (Production-Grade Arabic Normalizer).
    تستخدم جداول التحويل المباشرة C-level (str.translate) لتحقيق سرعة تنفيذ قصوى مع استهلاك أدنى للذاكرة.
    """

    __slots__ = ("_trans_table", "_punct_regex", "_spaces_regex")
    def __init__(self):
            
            # 1. خريطة الاستبدال لتوحيد الأحرف والأرقام
            replacement_map: Dict[str, str] = {
                "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ؤ": "ا", "ئ": "ا",
                "ى": "ي", "ة": "ه",
                "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
                "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
            }

            # 2. إنشاء جدول التبديل الأساسي من القاموس
            self._trans_table = str.maketrans(replacement_map)

            # 3. تجميع كافة أحرف التشكيل والتطويل لإزالتها
            tashkeel_chars = (
                "".join([chr(i) for i in range(0x064B, 0x0653)])
                + "\u0640"
                + "\u0617\u0618\u0619\u061A\u0653\u0654\u0655"
            )
            
            # 4. دمج جدول الحذف (تفريغ الحركات) في نفس الجدول باستخدام التحديث المباشر
            for char in tashkeel_chars:
                self._trans_table[ord(char)] = None

            # 5. أنماط التنظيف الإضافية
            self._punct_regex = re.compile(r"[^\w\s]", re.UNICODE)
            self._spaces_regex = re.compile(r"\s+")
    def normalize(self, text: str) -> str:
        """تستقبل النص الخام وترجع نصاً معالجاً وموحداً بسرعة استجابة فائقة."""
        if not text or not isinstance(text, str):
            return ""

        # الخطوة 1: التنفيذ المباشر للاستبدال والحذف بداخل C (فائق السرعة)
        normalized = text.translate(self._trans_table)

        # الخطوة 2: إزالة علامات الترقيم والرموز
        normalized = self._punct_regex.sub(" ", normalized)

        # الخطوة 3: ضغط المسافات وتنظيف الأطراف
        normalized = self._spaces_regex.sub(" ", normalized)

        return normalized.strip()


# ==========================================
# اختبار الأداء وتأكيد صحة العمل (Quick Test)
# ==========================================
if __name__ == "__main__":
    import time

    normalizer = ArabicNormalizer()

    sample_query = "مَتَى حِصّةُ الرِّياضِيَاتِ لِلصَّفِّ 3/1 يَوْمَ الأَحَدِ؟ (أُستَاذ: أَحْمَد)"

    # قياس زمن التنفيذ
    start_time = time.perf_counter()
    result = normalizer.normalize(sample_query)
    end_time = time.perf_counter()

    print("--- اختبار وحدة التوحيد ---")
    print("النص الأصلي :", sample_query)
    print("النص المعالج:", result)
    print(f"زمن المعالجة: {(end_time - start_time) * 1000:.4f} ملي ثانية")