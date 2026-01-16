from django.urls import path
from . import views

urlpatterns = [
    path('', views.statistics, name='analytics'),
    path('performance-report/', views.performance_report, name='analytics_performance_report'),
]

