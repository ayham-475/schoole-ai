from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# استيراد النماذج (Pydantic Models)
from assistant_api.models import ChatRequest, ChatResponse

# استيراد وحدات الذكاء الاصطناعي (AI Engine)
from ai_engine.arabic_normalizer import ArabicNormalizer
from ai_engine.nlp_processor import NLPProcessor
from ai_engine.inference_engine import InferenceEngine
from ai_engine.response_generator import ResponseGenerator

# إعداد الـ Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# تهيئة تطبيق FastAPI
app = FastAPI(
    title="School Expert System API",
    description="واجهة برمجية لتقديم إجابات ذكية للطلاب وأولياء الأمور بالاعتماد على قاعدة معرفة علائقية (JSON).",
    version="1.0.0"
)

# تفعيل CORS للسماح للواجهات الأمامية بالاتصال بالـ API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# تحميل المحركات في الذاكرة مرة واحدة عند إقلاع الخادم (Singletons)
# ---------------------------------------------------------
logger.info("جاري تهيئة محركات الذكاء الاصطناعي...")
normalizer = ArabicNormalizer()
nlp_processor = NLPProcessor()
inference_engine = InferenceEngine(kb_path="knowledge_base")
response_generator = ResponseGenerator()
logger.info("تمت تهيئة المحركات بنجاح وتجهيز واجهة API.")

# ---------------------------------------------------------
# Endpoints (نقاط الاتصال)
# ---------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """نقطة فحص سريعة للتأكد من أن الخادم يعمل والمحركات جاهزة."""
    return {"status": "online", "knowledge_base_loaded": True}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    الـ Endpoint الرئيسي لمعالجة استعلامات المستخدم.
    """
    try:
        user_query = request.query
        
        # 1. تنظيف النص (Normalization)
        normalized_text = normalizer.normalize(user_query)
        
        # 2. استخراج النية والكيانات (NLP Processing)
        nlp_result = nlp_processor.process_query(normalized_text)
        
        # 3. الاستدلال وجلب البيانات (Inference & Relational JOINs)
        inference_result = inference_engine.execute_query(
            intent=nlp_result.intent, 
            entities=nlp_result.entities
        )
        
        # 4. توليد الرد النهائي (Response Generation)
        final_text = response_generator.generate_response(
            intent=nlp_result.intent,
            inference_result=inference_result,
            entities=nlp_result.entities
        )
        
        # إرجاع الاستجابة متوافقة مع Pydantic Model
        return ChatResponse(
            response=final_text,
            intent_detected=nlp_result.intent,
            entities_extracted=nlp_result.entities,
            sources=inference_result.sources_used,
            confidence_score=nlp_result.confidence
        )
        
    except Exception as e:
        logger.error(f"حدث خطأ أثناء معالجة الطلب: {str(e)}")
        raise HTTPException(status_code=500, detail="حدث خطأ داخلي في الخادم أثناء معالجة استعلامك.")