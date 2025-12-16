from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_panel, name='admin_panel'),
    path('account/edit/', views.edit_own_account, name='edit_own_account'),
    path('team/add/', views.team_add_member, name='team_add_member'),
    path('team/<int:pk>/edit/', views.edit_team_member, name='edit_team_member'),
    path('team/<int:pk>/remove/', views.team_remove_member, name='team_remove_member'),
]

