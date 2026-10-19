from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('perfil/', views.perfil_publico, name='perfil-publico'),
    path('tecnologias/', views.tecnologias_publicas, name='tecnologias-publicas'),
    path(
        'experiencias/',
        views.experiencias_publicas,
        name='experiencias-publicas',
    ),
    path('formacion/', views.formacion_publica, name='formacion-publica'),
]
