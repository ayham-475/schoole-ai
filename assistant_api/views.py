
import json
import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import render

# استيراد محركات الذكاء الاصطناعي
from ai_engine.arabic_normalizer import ArabicNormalizer
from ai_engine.nlp_processor import NLPProcessor
from ai_engine.inference_engine import InferenceEngine
from ai_engine.response_generator import ResponseGenerator

# استيراد نموذج سجل المحادثات
from .models import ChatLog

# تهيئة المحركات ككائنات دائمة في الذاكرة لتسريع زمن الاستجابة
normalizer = ArabicNormalizer()
nlp_processor = NLPProcessor()
inference_engine = InferenceEngine(knowledge_base_path="knowledge_base")
response_generator = ResponseGenerator()


@csrf_exempt
@require_POST
def chat_view(request):
    """
    نقطة النهاية لاستقبال رسائل المستخدم ومعالجتها وإرجاع الرد الذكي الموثق.
    """
    try:
        data = json.loads(request.body)
        user_query = data.get("query", "").strip()

        if not user_query:
            return JsonResponse({"error": "حقل الاستعلام (query) مطلوب."}, status=400)

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

        # 7. حفظ المحادثة في قاعدة البيانات للإحصاء والتحسين
        try:
            ChatLog.objects.create(
                query=user_query,
                response=final_text,
                intent_detected=nlp_result.intent,
                confidence_score=calc_confidence
            )
        except Exception as db_err:
            print(f"Warning: Failed to log chat to DB: {db_err}")

        # 8. إرجاع الرد للواجهة الأمامية
        return JsonResponse({
            "response": final_text,
            "intent_detected": nlp_result.intent,
            "entities_extracted": nlp_result.entities,
            "sources": sources_labels,
            "confidence_score": calc_confidence
        }, status=200)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': f"حدث خطأ أثناء معالجة الطلب: {str(e)}"}, status=500)


def home_view(request):
    """عرض الواجهة التفاعلية الرئيسية للمساعد الذكي"""
    return render(request, 'index.html')