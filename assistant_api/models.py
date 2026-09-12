from django.db import models


class ChatLog(models.Model):
    """
    نموذج لتخزين استعلامات المستخدمين وردود النظام الذكي في قاعدة البيانات.
    """
    query = models.TextField(
        verbose_name="استعلام المستخدم",
        help_text="النص الخام أو المعالج الذي أرسله الطالب أو ولي الأمر."
    )

    response = models.TextField(
        verbose_name="رد النظام",
        help_text="الرد النهائي المنسق بلغة Markdown الذي تم إرجاعه للمستخدم."
    )

    intent_detected = models.CharField(
        max_length=100,
        verbose_name="النية المكتشفة",
        help_text="النية التصنيفية المستخرجة بواسطة محرك الـ NLP (مثل query_schedule)."
    )

    confidence_score = models.FloatField(
        default=0.0,
        verbose_name="نسبة الثقة",
        help_text="درجة الثقة في دقة تحليل الاستعلام وتتراوح بين 0.0 و 1.0."
    )

    response_time_ms = models.IntegerField(
        default=0,
        verbose_name="زمن الاستجابة (ملي ثانية)",
        help_text="الزمن المستغرق لمعالجة الاستعلام وإنتاج الرد بالمللي ثانية."
    )

    session_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name="معرف الجلسة",
        help_text="معرف فريد لجلسة المستخدم لتتبع المحادثات المتسلسلة."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="وقت الاستعلام",
        help_text="التاريخ والوقت الذي تم فيه تنفيذ الاستعلام وتخزينه."
    )

    class Meta:
        verbose_name = "سجل محادثة"
        verbose_name_plural = "سجلات المحادثات"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.query[:40]}... ({self.intent_detected})"


class Feedback(models.Model):
    """
    نموذج لتخزين تقييمات المستخدمين لجودة الردود (👍 مفيدة / 👎 غير مفيدة).
    """
    query = models.TextField(
        verbose_name="الاستعلام",
        help_text="نص الاستعلام الأصلي الذي تم تقييم رده."
    )

    response = models.TextField(
        verbose_name="الرد",
        help_text="نص الرد الذي تم تقييمه من قبل المستخدم."
    )

    is_positive = models.BooleanField(
        verbose_name="تقييم إيجابي",
        help_text="True إذا كان التقييم إيجابياً (👍)، False إذا كان سلبياً (👎)."
    )

    session_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name="معرف الجلسة"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="وقت التقييم"
    )

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
        ordering = ["-created_at"]

    def __str__(self):
        sentiment = '👍' if self.is_positive else '👎'
        return f"{sentiment} {self.query[:40]}..."