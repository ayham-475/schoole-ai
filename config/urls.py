from django.contrib import admin
from django.urls import path
from assistant_api.views import chat_view, home_view, feedback_view, stats_view, dashboard_view

urlpatterns = [
    path('', home_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('admin/', admin.site.urls),
    path('api/chat/', chat_view, name='api_chat'),
    path('api/feedback/', feedback_view, name='api_feedback'),
    path('api/stats/', stats_view, name='api_stats'),
]