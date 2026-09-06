from django.contrib import admin
from .models import ChatLog, Feedback


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    """لوحة إدارة سجلات المحادثات مع بحث وتصفية متقدمة."""
    list_display = ('short_query', 'intent_detected', 'confidence_badge', 'response_time_ms', 'created_at')
    list_filter = ('intent_detected', 'created_at')
    search_fields = ('query', 'response', 'intent_detected')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 30

    def short_query(self, obj):
        return obj.query[:60] + '...' if len(obj.query) > 60 else obj.query
    short_query.short_description = 'الاستعلام'

    def confidence_badge(self, obj):
        score = obj.confidence_score
        if score >= 0.9:
            color = '#15803d'
        elif score >= 0.7:
            color = '#ca8a04'
        else:
            color = '#dc2626'
        return f'{score:.0%}'
    confidence_badge.short_description = 'الثقة'


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """لوحة إدارة تقييمات المستخدمين."""
    list_display = ('short_query', 'sentiment_icon', 'created_at')
    list_filter = ('is_positive', 'created_at')
    search_fields = ('query', 'response')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 30

    def short_query(self, obj):
        return obj.query[:60] + '...' if len(obj.query) > 60 else obj.query
    short_query.short_description = 'الاستعلام'

    def sentiment_icon(self, obj):
        return '👍 مفيدة' if obj.is_positive else '👎 غير مفيدة'
    sentiment_icon.short_description = 'التقييم'
