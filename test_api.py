import time
import json
from django.test import TestCase, Client

class SchoolAITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.expected_keys = ["response", "intent_detected", "confidence_score", "sources"]

    def assertValidResponse(self, response):
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for key in self.expected_keys:
            self.assertIn(key, data)

    def test_greeting_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "السلام عليكم ورحمة الله"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_location_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "وين تقع مدرسة الرواد ورقم التواصل؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_schedule_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "متى حصة الرياضيات للصف الثالث الثانوي يوم الأحد؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_teacher_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "مين هو معلم الفيزياء لثالث ثانوي؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_curriculum_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "ايش هي كتب الصف العاشر؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_calendar_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "متى تبدا اجازه عيد الفطر؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_discipline_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "ايش عقوبة الهروب من المدرسة؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_grading_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "كم نسبة توزيع درجات النهائي؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_admission_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "ابغى اسجل ولدي في المدرسة ايش الشروط؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_facilities_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "وين العيادة الطبية المدرسية وما هي مواعيدها؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_attendance_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "عندي عذر طبي كيف اقدمه وكم مهلة التقديم؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_honor_roll_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "ايش شروط الانضمام للوحة الشرف؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_out_of_scope_scenario(self):
        response = self.client.post('/api/chat/', data=json.dumps({"query": "كيف أطبخ كبسة دجاج في البيت؟"}), content_type='application/json')
        self.assertValidResponse(response)

    def test_performance(self):
        start_time = time.time()
        response = self.client.post('/api/chat/', data=json.dumps({"query": "السلام عليكم"}), content_type='application/json')
        end_time = time.time()
        self.assertLess(end_time - start_time, 2.0, "Response took longer than 2 seconds")
        self.assertValidResponse(response)

    def test_feedback_endpoint(self):
        response = self.client.post('/api/feedback/', data=json.dumps({"rating": 5, "comment": "Great!"}), content_type='application/json')
        self.assertIn(response.status_code, [200, 201])

    def test_stats_endpoint(self):
        response = self.client.get('/api/stats/')
        self.assertEqual(response.status_code, 200)