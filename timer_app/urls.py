from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='timer_app/login.html'), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='timer_app/password_reset.html',
             email_template_name='timer_app/password_reset_email.html',
             subject_template_name='timer_app/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='timer_app/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='timer_app/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='timer_app/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Admin Panel
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/account/edit/', views.edit_own_account, name='edit_own_account'),
    path('admin-panel/team/add/', views.team_add_member, name='team_add_member'),
    path('admin-panel/team/<int:pk>/edit/', views.edit_team_member, name='edit_team_member'),
    path('admin-panel/team/<int:pk>/remove/', views.team_remove_member, name='team_remove_member'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.customer_add, name='customer_add'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # Projects
    path('projects/', views.project_list, name='project_list'),
    path('projects/add/', views.project_add, name='project_add'),
    path('projects/<int:pk>/', views.project_detail, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('projects/<int:pk>/complete/', views.project_complete, name='project_complete'),
    
    # Global Timers
    path('timers/', views.timer_list, name='timer_list'),
    path('timers/create/', views.timer_create, name='timer_create'),
    path('timers/<int:pk>/edit-global/', views.timer_edit_global, name='timer_edit_global'),
    path('timers/<int:pk>/delete-global/', views.timer_delete_global, name='timer_delete_global'),
    
    # Project Timers
    path('timers/running/', views.running_timers, name='running_timers'),
    path('timers/assign/', views.timer_assign_to_project, name='timer_assign_to_project'),
    path('project-timers/<int:pk>/remove/', views.project_timer_remove, name='project_timer_remove'),
    path('project-timers/<int:pk>/start/', views.timer_start, name='timer_start'),
    path('project-timers/<int:pk>/stop/', views.timer_stop, name='timer_stop'),
    
    # Sessions
    path('sessions/<int:pk>/note/', views.session_update_note, name='session_update_note'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
]

