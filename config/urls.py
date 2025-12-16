"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('timer.urls')),
    path('analytics/', include('analytics.urls')),
    path('customers/', include('customers.urls')),
    path('projects/', include('projects.urls')),
    path('admin-panel/', include('workspace_admin.urls')),
]

