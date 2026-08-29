from django.contrib import admin
from django.urls import path
from assistant_api.views import chat_view, home_view

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/chat/', chat_view, name='api_chat'),
]