from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app.core.views import HomeView, DashboardView,PerfilView
from app.core.view.Modulo_deteccion_Enfermedades.Deteccion_enfermedad_view import DeteccionListView,DeteccionAnalisisView,DetalleAnalisisView
from app.core.view.Modulo_Alerta_Comunitaria.Alerta_comunitaria_view import AlertasComunitariasView
from app.core.view.Modulo_Gestion_campo.gestion_campos import (
    GestionCampoListView,
    RegistroCampoCreateView,
    RegistroCampoUpdateView,
    RegistroCampoDeleteView,
)

from app.core.view.Modulo_recomedaciones.recomendaciones import recomendaciones
from app.core.view.Modulo_Estadistica.estadistica_view import estadisticas_view

from app.core.view.plantacion_view import verificar_plantacion, registro_plantacion, obtener_direccion
app_name = 'core'

urlpatterns = [
    # Home View
    path('', HomeView.as_view(), name='home'),
    
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('deteccion/', DeteccionListView.as_view(), name='deteccion_list'),
    path('deteccion/analizar/', DeteccionAnalisisView.as_view(), name='deteccion_analizar'),
    path('deteccion/detalle/<int:id>/', DetalleAnalisisView.as_view(), name='deteccion_detalle'),
    path('alertas/', AlertasComunitariasView.as_view(), name='alertas'),
    
    
    path('verificar-plantacion/', verificar_plantacion, name='verificar_plantacion'),
    path('registro-plantacion/', registro_plantacion, name='registro_plantacion'),
    path('api/direccion/', obtener_direccion, name='obtener_direccion'),

    path('gestion_campo/', GestionCampoListView.as_view(), name='gestion_campo'),
    path('campo/crear/', RegistroCampoCreateView.as_view(), name='registrocampo_create'),
    path('campo/<int:pk>/editar/', RegistroCampoUpdateView.as_view(), name='registrocampo_edit'),
    path('campo/<int:pk>/eliminar/', RegistroCampoDeleteView.as_view(), name='registrocampo_delete'),


    path('recomendaciones/', recomendaciones, name='recomendaciones'),
    
    path('estadisticas/', estadisticas_view, name='estadisticas'),  
    
    path('perfil/', PerfilView.as_view(), name='perfil'),  
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
