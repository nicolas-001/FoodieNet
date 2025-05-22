app_name = 'authentication'

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views  # tus vistas personalizadas, ej. registro

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='authentication:login'), name='logout'),
    path('register/', views.register, name='register'),  # vista que crea usuarios nuevos
    ]
