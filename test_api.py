import requests

url = "http://127.0.0.1:8000/api/chat/"
payload = {"query": "متى حصة الرياضيات للصف الثالث الثانوي يوم الأحد؟"}

response = requests.post(url, json=payload)

print("Status Code:", response.status_code)
print("Response JSON:", response.json())