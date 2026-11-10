import json
from django.shortcuts import render
from django.views import View
from datetime import timedelta
from django.utils import timezone
from app.core.models import Plantacion, PerfilUsuario, ResultadoAnalisis, AlertaComunitaria
from app.core.mixins import PlantacionRequeridaMixin ,LoginRequiredMixin


class HomeView(View):
    def get(self, request):
        return render(request, 'core/home.html')
    
class PerfilView(LoginRequiredMixin, View):
    template_name = 'security/config/perfil.html'

    def get(self, request):
        user = request.user
        context = {
            'user': user,
            'perfil_usuario': PerfilUsuario.objects.filter(user=user).first(),
            'plantaciones': Plantacion.objects.filter(usuario=user),
            'active_module': 'admin',
        }
        return render(request, self.template_name, context)
class DashboardView(PlantacionRequeridaMixin, View):
    def get(self, request):
        user = request.user
        plantaciones_todas = Plantacion.objects.all()
        plantacion_id = request.GET.get('plantacion_id')
        
    
        plantaciones_usuario = Plantacion.objects.filter(usuario=user)
        

        if plantacion_id:
            try:
                plantacion_principal = Plantacion.objects.get(id=plantacion_id, usuario=user)
            except Plantacion.DoesNotExist:
                plantacion_principal = plantaciones_usuario.first() if plantaciones_usuario.exists() else None
        else:
            plantacion_principal = plantaciones_usuario.first() if plantaciones_usuario.exists() else None

        perfil_usuario, _ = PerfilUsuario.objects.get_or_create(user=user)

        coordenadas_plantaciones = []
        for plantacion in plantaciones_todas:
            if plantacion.latitud and plantacion.longitud:
                try:
                    lat = float(plantacion.latitud)
                    lng = float(plantacion.longitud)
                    if -90 <= lat <= 90 and -180 <= lng <= 180:
                        propietario = f"{plantacion.usuario.first_name} {plantacion.usuario.last_name}" if plantacion.usuario else "Sin propietario"
                        
              
                        extension = plantacion.extension_hectareas
                        if extension is not None:
                            extension = float(extension)
                        else:
                            extension = 0
                        
                        coordenadas_plantaciones.append({
                            'id': plantacion.id,
                            'nombre': plantacion.nombre_finca,
                            'latitud': lat,
                            'longitud': lng,
                            'ubicacion': plantacion.ubicacion,
                            'extension_hectareas': extension,
                            'fecha_registro': plantacion.fecha_registro.strftime('%d/%m/%Y') if hasattr(plantacion, 'fecha_registro') and plantacion.fecha_registro else 'No especificado',
                            'propietario': propietario
                        })
                except (ValueError, TypeError) as e:
                    print(f"Error procesando coordenadas de plantación {plantacion.id}: {e}")
                    continue

        print(f"Total de plantaciones con coordenadas válidas: {len(coordenadas_plantaciones)}")

        # Indicadores reales de la plantación principal
        analisis = ResultadoAnalisis.objects.filter(imagen__plantacion=plantacion_principal)
        total_analisis = analisis.count()
        sanas = analisis.filter(enfermedad_detectada__iexact='Banana Healthy Leaf').count()
        salud = round(sanas * 100 / total_analisis) if total_analisis else None
        alertas_recientes = AlertaComunitaria.objects.filter(
            usuario_destino=user,
            fecha_alerta__gte=timezone.now() - timedelta(days=30),
        ).count()

        context = {
            'total_analisis': total_analisis,
            'salud_cultivo': salud,
            'alertas_recientes': alertas_recientes,
            'ultimo_analisis': analisis.order_by('-fecha_analisis').first(),
            'coordenadas_plantaciones_json': json.dumps(coordenadas_plantaciones),
            'plantacion_principal': plantacion_principal,
            'plantaciones_usuario': plantaciones_usuario,
            'perfil_usuario': perfil_usuario,
        }

        return render(request, 'core/Dashboard/inicio.html', context)


