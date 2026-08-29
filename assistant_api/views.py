import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# استيراد محركات الذكاء الاصطناعي
from ai_engine.arabic_normalizer import ArabicNormalizer
from ai_engine.nlp_processor import NLPProcessor
from ai_engine.inference_engine import InferenceEngine
from ai_engine.response_generator import ResponseGenerator

# استيراد نموذج قاعدة البيانات الذي أنشأناه للتو
from .models import ChatLog
from django.shortcuts import render

# تهيئة المحركات مرة واحدة عند تحميل التطبيق لتسريع الاستجابة
normalizer = ArabicNormalizer()
nlp_processor = NLPProcessor()
inference_engine = InferenceEngine(knowledge_base_path="knowledge_base")
response_generator = ResponseGenerator()
@csrf_exempt
@require_POST
def chat_view(request):
    """
    Django View لاستقبال رسائل المستخدم، معالجتها عبر الـ AI Engine، وإرجاع الرد.
    """
    try:
        # قراءة البيانات المرسلة بصيغة JSON
        data = json.loads(request.body)
        user_query = data.get("query", "").strip()

        if not user_query:
            return JsonResponse({"error": "حقل الاستعلام (query) مطلوب."}, status=400)

        # 1. تنظيف النص
        normalized_text = normalizer.normalize(user_query)

        # 2. استخراج النية والكيانات
        nlp_result = nlp_processor.process_query(normalized_text)

        # 3. الاستدلال وجلب البيانات من قاعدة المعرفة
        inference_result = inference_engine.execute_query(
            user_query=user_query,  # <-- تم إضافة هذا السطر الهام جداً
            intent=nlp_result.intent,
            entities=nlp_result.entities
        )

        # 4. توليد الرد النهائي
        final_text = response_generator.generate_response(
            intent=nlp_result.intent,
            inference_result=inference_result,
            entities=nlp_result.entities
        )

        # 5. حفظ المحادثة في قاعدة البيانات
        ChatLog.objects.create(
            query=user_query,
            response=final_text,
            intent_detected=nlp_result.intent,
            confidence_score=nlp_result.confidence
        )

        # إرجاع الرد للـ Frontend
        return JsonResponse({
            "response": final_text,
            "intent_detected": nlp_result.intent,
            "entities_extracted": nlp_result.entities,
            "sources": [],  # <-- تم التعديل هنا لتفادي الخطأ (قائمة فارغة بدلاً من sources_used)
            "confidence_score": nlp_result.confidence
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f"حدث خطأ في الخادم: {str(e)}"}, status=500)
def home_view(request):
    return render(request, 'index.html')


