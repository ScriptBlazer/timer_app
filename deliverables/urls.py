from django.urls import path
from . import views

app_name = 'deliverables'

urlpatterns = [
    path('projects/<int:project_pk>/deliverables/', views.deliverable_list, name='deliverable_list'),
    path('projects/<int:project_pk>/deliverables/add/', views.deliverable_add, name='deliverable_add'),
    path('projects/<int:project_pk>/deliverables/add-ajax/', views.deliverable_add_ajax, name='deliverable_add_ajax'),
    path('deliverables/<int:pk>/', views.deliverable_detail, name='deliverable_detail'),
    path('deliverables/<int:pk>/edit/', views.deliverable_edit, name='deliverable_edit'),
    path('deliverables/<int:pk>/delete/', views.deliverable_delete, name='deliverable_delete'),
]


