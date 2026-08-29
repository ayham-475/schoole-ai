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