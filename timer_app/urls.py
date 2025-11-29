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
    
    # Timers
    path('timers/running/', views.running_timers, name='running_timers'),
    path('timers/add/', views.timer_add, name='timer_add'),
    path('timers/<int:pk>/', views.timer_detail, name='timer_detail'),
    path('timers/<int:pk>/edit/', views.timer_edit, name='timer_edit'),
    path('timers/<int:pk>/delete/', views.timer_delete, name='timer_delete'),
    path('timers/<int:pk>/start/', views.timer_start, name='timer_start'),
    path('timers/<int:pk>/stop/', views.timer_stop, name='timer_stop'),
    
    # Sessions
    path('sessions/<int:pk>/note/', views.session_update_note, name='session_update_note'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
]

