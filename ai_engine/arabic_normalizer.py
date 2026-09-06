import re
import string
from typing import Dict, List, Set


class ArabicNormalizer:
    """
    وحدة معالجة وتوحيد النص العربي عالية الأداء والذكاء (Production-Grade Arabic Normalizer).
    - توحيد الأحرف والأرقام وإزالة التشكيل والتطويل عبر str.translate فائق السرعة.
    - دعم اللهجات المحكية (اليمنية، الخليجية، الشامية، المصرية) وتحويلها إلى مقابلاتها الفصحى لتسهيل الاستدلال.
    - استخراج الكلمات الدلالية المفتاحية (Keyword Extraction) بعد تنقية حروف الجر وأدوات الاستفهام.
    """

    __slots__ = ("_trans_table", "_punct_regex", "_spaces_regex", "_dialect_map", "_stop_words")

    def __init__(self):
        # 1. خريطة الاستبدال لتوحيد الأحرف والأرقام
        replacement_map: Dict[str, str] = {
            "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ؤ": "ا", "ئ": "ا",
            "ى": "ي", "ة": "ه",
            "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
            "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
        }

        # 2. إنشاء جدول التبديل الأساسي
        self._trans_table = str.maketrans(replacement_map)

        # 3. تجميع أحرف التشكيل والتطويل لإزالتها
        tashkeel_chars = (
            "".join([chr(i) for i in range(0x064B, 0x0653)])
            + "\u0640"
            + "\u0617\u0618\u0619\u061A\u0653\u0654\u0655"
        )
        for char in tashkeel_chars:
            self._trans_table[ord(char)] = None

        # 4. تعبيرات التنظيف (مع الإبقاء على / للشعب مثل 3/1)
        self._punct_regex = re.compile(r"[^\w\s/]", re.UNICODE)
        self._spaces_regex = re.compile(r"\s+")

        # 5. قاموس اللهجات المحكية وتحويلها إلى الفصحى الموحدة
        self._dialect_map = {
            "وين": "اين",
            "فين": "اين",
            "ايش": "ماذا",
            "اي": "اي",
            "شو": "ماذا",
            "شنو": "ماذا",
            "ليش": "لماذا",
            "ليه": "لماذا",
            "حق": "خاص",
            "ابغى": "اريد",
            "ابغا": "اريد",
            "ابي": "اريد",
            "اشتي": "اريد",
            "بدنا": "نريد",
            "بدي": "اريد",
            "مين": "من",
            "منهو": "من",
            "ذلحين": "الان",
            "هالحين": "الان",
            "دحين": "الان",
            "عشان": "بسبب",
            "علشان": "بسبب",
            "كمين": "كم",
            "يقدر": "يستطيع",
            "اقدر": "استطيع",
            "نقدر": "نستطيع"
        }

        # 6. قائمة الكلمات الشائعة / التوقف (Stop Words) للاستخراج الدلالي
        self._stop_words: Set[str] = {
            "في", "من", "على", "إلى", "الى", "عن", "مع", "ب", "ل", "ك",
            "هل", "ما", "ماذا", "اين", "متى", "كيف", "كم", "لماذا",
            "لو", "سمحت", "تفضل", "اريد", "معرفة", "السؤال", "استفسار",
            "ممكن", "يا", "اخي", "لوتكرمت", "ارغب", "ودي", "بخصوص"
        }

    def normalize(self, text: str, handle_dialects: bool = True) -> str:
        """
        تستقبل النص الخام وترجع نصاً معالجاً وموحداً بسرعة فائقة.
        """
        if not text or not isinstance(text, str):
            return ""

        # الخطوة 1: استبدال الحروف وحذف التشكيل
        normalized = text.translate(self._trans_table)

        # الخطوة 2: إزالة علامات الترقيم
        normalized = self._punct_regex.sub(" ", normalized)

        # الخطوة 3: ضغط المسافات
        normalized = self._spaces_regex.sub(" ", normalized).strip()

        # الخطوة 4: توحيد اللهجات الشائعة
        if handle_dialects:
            tokens = normalized.split()
            tokens = [self._dialect_map.get(tok, tok) for tok in tokens]
            normalized = " ".join(tokens)

        return normalized

    def extract_keywords(self, text: str) -> List[str]:
        """
        تستخرج الكلمات المفتاحية الأساسية من الاستعلام بعد إزالة حروف الجر وأدوات الاستفهام.
        """
        normalized = self.normalize(text, handle_dialects=True)
        tokens = normalized.split()
        keywords = [
            t for t in tokens
            if t not in self._stop_words and len(t) > 1 and not t.isdigit()
        ]
        return keywords


if __name__ == "__main__":
    normalizer = ArabicNormalizer()
    samples = [
        "وين مكتب أستاذ أحمد محمود؟ لو سمحت",
        "ايش عقوبة الهروب من المدرسة يا أستاذ؟",
        "ابغى اعرف متى حِصّةُ الرِّيَاضِيَّاتِ للصف 3/1 يوم الأحد؟",
        "اشتي اسجل ابني في المدرسة ايش الشروط؟"
    ]

    for s in samples:
        norm = normalizer.normalize(s)
        kws = normalizer.extract_keywords(s)
        print("الأصل:", s)
        print("المعالج:", norm)
        print("الكلمات المفتاحية:", kws)
        print("-" * 50)