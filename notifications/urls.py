from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('todas/', views.ver_todas, name='ver_todas'),
]
