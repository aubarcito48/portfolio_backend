from django.urls import path

from . import views
from .aubar_views import chat
from .whatsapp import webhook
from .contact import contact

app_name = 'portfolio'

urlpatterns = [
    path('contacto/', contact, name='contact'),
    path('whatsapp/webhook/', webhook, name='whatsapp-webhook'),
    path('chat/', chat, name='aubar-chat'),
    path('perfil/', views.perfil_publico, name='perfil-publico'),
    path('tecnologias/', views.tecnologias_publicas, name='tecnologias-publicas'),
    path(
        'experiencias/',
        views.experiencias_publicas,
        name='experiencias-publicas',
    ),
    path('formacion/', views.formacion_publica, name='formacion-publica'),
    path('enlaces/', views.enlaces_publicos, name='enlaces-publicos'),
    path('proyectos/', views.proyectos_publicos, name='proyectos-publicos'),
    path(
        'proyectos/<slug:slug>/',
        views.detalle_proyecto_publico,
        name='detalle-proyecto-publico',
    ),
]
