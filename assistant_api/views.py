import json
import time
import logging
from collections import defaultdict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render
from django.utils import timezone

# استيراد محركات الذكاء الاصطناعي
from ai_engine.arabic_normalizer import ArabicNormalizer
from ai_engine.nlp_processor import NLPProcessor
from ai_engine.inference_engine import InferenceEngine
from ai_engine.response_generator import ResponseGenerator

# استيراد نماذج قاعدة البيانات
from .models import ChatLog, Feedback

# نظام التسجيل الاحترافي
logger = logging.getLogger('assistant_api')

# تهيئة المحركات ككائنات دائمة في الذاكرة لتسريع زمن الاستجابة
normalizer = ArabicNormalizer()
nlp_processor = NLPProcessor()
inference_engine = InferenceEngine(knowledge_base_path="knowledge_base")
response_generator = ResponseGenerator()

# ======================================
# نظام تحديد المعدل (Rate Limiting)
# ======================================
_rate_limit_cache = defaultdict(list)
RATE_LIMIT_MAX = 30       # الحد الأقصى للطلبات
RATE_LIMIT_WINDOW = 60    # نافذة الوقت بالثواني


def _check_rate_limit(ip: str) -> bool:
    """التحقق مما إذا كان العميل قد تجاوز الحد الأقصى للطلبات."""
    now = time.time()
    _rate_limit_cache[ip] = [t for t in _rate_limit_cache[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_cache[ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_cache[ip].append(now)
    return True


def _get_client_ip(request):
    """استخراج عنوان IP الحقيقي للعميل."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR', '')


# ======================================
# نقطة النهاية الرئيسية: الدردشة
# ======================================
@csrf_exempt
@require_POST
def chat_view(request):
    """
    نقطة النهاية لاستقبال رسائل المستخدم ومعالجتها وإرجاع الرد الذكي الموثق.
    """
    # التحقق من حد المعدل
    client_ip = _get_client_ip(request)
    if not _check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JsonResponse(
            {"error": "تم تجاوز الحد الأقصى للطلبات. يرجى الانتظار قليلاً ثم المحاولة مجدداً."},
            status=429
        )

    start_time = time.time()

    try:
        data = json.loads(request.body)
        user_query = data.get("query", "").strip()

        if not user_query:
            return JsonResponse({"error": "حقل الاستعلام (query) مطلوب."}, status=400)

        if len(user_query) > 500:
            return JsonResponse({"error": "الاستعلام طويل جداً. الحد الأقصى 500 حرف."}, status=400)

        logger.info(f"New query from {client_ip}: {user_query[:80]}...")

        # 1. تنظيف وتوحيد النص ودعم العامية
        normalized_text = normalizer.normalize(user_query)

        # 2. استخراج النية والكيانات
        nlp_result = nlp_processor.process_query(normalized_text)

        # 3. الاستدلال وجلب البيانات الموثوقة من ملفات المعرفة
        inference_result = inference_engine.run_query(
            user_query=user_query,
            intent=nlp_result.intent,
            entities=nlp_result.entities
        )

        # 4. توليد الرد النهائي المنسق
        final_text = response_generator.generate_response(
            intent=nlp_result.intent,
            inference_result=inference_result,
            entities=nlp_result.entities
        )

        # 5. استخراج المصادر المعتمدة
        sources_labels = [
            inference_engine.SOURCE_LABELS.get(s, s)
            for s in getattr(inference_result, 'sources_used', [])
        ]

        # 6. حساب نسبة الثقة التراكمية
        calc_confidence = round(
            max(nlp_result.confidence, getattr(inference_result, 'confidence', 0.8)), 2
        )

        # 7. حساب زمن الاستجابة
        response_time_ms = int((time.time() - start_time) * 1000)

        # 8. حفظ المحادثة في قاعدة البيانات للإحصاء والتحسين
        try:
            ChatLog.objects.create(
                query=user_query,
                response=final_text,
                intent_detected=nlp_result.intent,
                confidence_score=calc_confidence,
                response_time_ms=response_time_ms
            )
        except Exception as db_err:
            logger.warning(f"Failed to log chat to DB: {db_err}")

        logger.info(f"Response sent | intent={nlp_result.intent} | confidence={calc_confidence} | time={response_time_ms}ms")

        # 9. إرجاع الرد للواجهة الأمامية
        return JsonResponse({
            "response": final_text,
            "intent_detected": nlp_result.intent,
            "entities_extracted": nlp_result.entities,
            "sources": sources_labels,
            "confidence_score": calc_confidence
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "صيغة JSON غير صالحة."}, status=400)
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return JsonResponse({'error': f"حدث خطأ أثناء معالجة الطلب: {str(e)}"}, status=500)


# ======================================
# نقطة النهاية: التقييم (Feedback)
# ======================================
@csrf_exempt
@require_POST
def feedback_view(request):
    """حفظ تقييم المستخدم لجودة الرد (👍/👎)."""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        response_text = data.get('response', '').strip()
        is_positive = data.get('is_positive', True)

        if not query or not response_text:
            return JsonResponse({'error': 'حقول الاستعلام والرد مطلوبة.'}, status=400)

        Feedback.objects.create(
            query=query,
            response=response_text,
            is_positive=is_positive
        )

        emoji = '👍' if is_positive else '👎'
        logger.info(f"Feedback received: {emoji} for query: {query[:40]}")
        return JsonResponse({'status': 'success', 'message': 'شكراً لتقييمك!'}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'صيغة JSON غير صالحة.'}, status=400)
    except Exception as e:
        logger.error(f"Feedback error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ======================================
# نقطة النهاية: الإحصائيات (Stats)
# ======================================
@csrf_exempt
@require_GET
def stats_view(request):
    """إرجاع إحصائيات عامة عن استخدام النظام."""
    try:
        from django.db.models import Count, Avg

        total_chats = ChatLog.objects.count()
        today = timezone.now().date()
        today_chats = ChatLog.objects.filter(created_at__date=today).count()
        avg_confidence = ChatLog.objects.aggregate(avg=Avg('confidence_score'))['avg'] or 0
        avg_response_time = ChatLog.objects.aggregate(avg=Avg('response_time_ms'))['avg'] or 0
        top_intents = list(
            ChatLog.objects.values('intent_detected')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        total_feedback = Feedback.objects.count()
        positive_feedback = Feedback.objects.filter(is_positive=True).count()

        return JsonResponse({
            'total_chats': total_chats,
            'today_chats': today_chats,
            'avg_confidence': round(avg_confidence, 2),
            'avg_response_time_ms': round(avg_response_time),
            'top_intents': top_intents,
            'total_feedback': total_feedback,
            'positive_feedback': positive_feedback,
            'satisfaction_rate': round(positive_feedback / total_feedback * 100, 1) if total_feedback > 0 else 0
        })
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ======================================
# الصفحة الرئيسية
# ======================================
def home_view(request):
    """عرض الواجهة التفاعلية الرئيسية للمساعد الذكي."""
    return render(request, 'index.html')