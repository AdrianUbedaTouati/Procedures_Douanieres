from django.urls import path
from . import views

app_name = 'apps_authentication'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('password-reset/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/<uuid:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
    path('verify-email/<uuid:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_view, name='resend_verification'),
]