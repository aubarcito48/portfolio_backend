from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('perfil/', views.perfil_publico, name='perfil-publico'),
]
