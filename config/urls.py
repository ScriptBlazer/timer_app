"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from timer import views as timer_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', timer_views.health_check, name='health_check'),  # Public health check endpoint
    path('', include('timer.urls')),
    path('analytics/', include('analytics.urls')),
    path('customers/', include('customers.urls')),
    path('projects/', include('projects.urls')),
    path('', include('deliverables.urls')),
    path('admin-panel/', include('workspace_admin.urls')),
]

