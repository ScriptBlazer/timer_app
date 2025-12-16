from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='timer/login.html'), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Registration Approval
    path('registration/approve/<uuid:token>/', views.approve_registration, name='approve_registration'),
    path('registration/deny/<uuid:token>/', views.deny_registration, name='deny_registration'),
    path('registration/resend/<uuid:token>/', views.resend_approval_notification, name='resend_approval_notification'),
    
    # Password Reset
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='timer/password_reset.html',
             email_template_name='timer/password_reset_email.html',
             subject_template_name='timer/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='timer/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='timer/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='timer/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    
    
    # Global Timers
    path('timers/', views.timer_list, name='timer_list'),
    path('timers/create/', views.timer_create, name='timer_create'),
    path('timers/<int:pk>/edit-global/', views.timer_edit_global, name='timer_edit_global'),
    path('timers/<int:pk>/delete-global/', views.timer_delete_global, name='timer_delete_global'),
    path('timers/add-custom-color/', views.add_custom_color, name='add_custom_color'),
    
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

