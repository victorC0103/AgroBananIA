from django.utils import timezone
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.views.generic import ListView
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from app.core.models import ResultadoAnalisis, User, ImagenAnalisis, Plantacion, AlertaComunitaria
from AgroBananIA.utils.calcular_distancia import calcular_distancia, enviar_correo
from app.core.view.Modulo_Alerta_Comunitaria.Alerta_comunitaria_view import enviar_alerta_email, encontrar_usuarios_cercanos
from AgroBananIA.utils.diagnostic import (
    predict_with_resnet50,
    obtener_nombre_enfermedad,
    obtener_recomendaciones,
    segment_and_save,
    get_model_info,
    class_mapping
)
import os
import shutil
import logging
import numpy as np


logger = logging.getLogger(__name__)


class DeteccionAnalisisView(LoginRequiredMixin, View):

    template_name = 'core/Dashboard/Modulo Deteccion Enfermedades/deteccion_form.html'
    
    def get_context_data(self, **kwargs):

        context = {
            'modelo_disponible': False,
            'diagnostico': None,
            'diagnostico_numero': None,
            'probabilidad': None,
            'recomendaciones': "",
            'probabilidades_todas': None,
            'error_modelo': None,
            'imagenes': [],
            'imagen_original': None,
            'modelo_info': get_model_info(),
            'deteccion_guardada': False,
            'class_mapping': class_mapping,
        }
        context.update(kwargs)
        
        context.update({
            'resnet_disponible': context['modelo_disponible'],
            'resnet_diagnostico': context['diagnostico'],
            'resnet_diagnostico_numero': context['diagnostico_numero'],
            'resnet_probabilidad': context['probabilidad'],
            'resnet_recomendaciones': context['recomendaciones'],
            'resnet_probabilidades_todas': context['probabilidades_todas'],
            'resnet_error': context['error_modelo'],
        })
        
        return context
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        if request.POST.get('confirmar_alerta'):
            return self.confirmar_alerta(request)
        elif request.FILES.get('imagen'):
            return self.analizar_imagen(request)
        else:
            messages.error(request, "Solicitud inválida.")
            return redirect('core:deteccion_analizar')
    
    def confirmar_alerta(self, request):
        try:
            analisis_id = request.session.get('ultimo_analisis_id')
            analisis_tmp = request.session.get('analisis_tmp')

            if analisis_id:
                resultado_analisis = ResultadoAnalisis.objects.get(id=analisis_id)
                plantacion_usuario = resultado_analisis.imagen.plantacion
                diagnostico = resultado_analisis.enfermedad_detectada
                diagnostico_numero = request.session.get('diagnostico_numero')
                probabilidad = resultado_analisis.probabilidad

            elif analisis_tmp:
                try:
                    plantacion_usuario = Plantacion.objects.filter(usuario=request.user).first()
                    if not plantacion_usuario:
                        messages.error(request, "No se encontró una plantación para confirmar el análisis.")
                        return redirect('core:deteccion_analizar')

                    imagen_analisis = ImagenAnalisis.objects.create(
                        plantacion=plantacion_usuario,
                        imagen=analisis_tmp.get('imagen_original'),
                        contorno=analisis_tmp.get('contorno'),
                        overlay=analisis_tmp.get('overlay'),
                        damage=analisis_tmp.get('damage')
                    )

                    resultado_analisis = ResultadoAnalisis.objects.create(
                        imagen=imagen_analisis,
                        enfermedad_detectada=analisis_tmp.get('diagnostico'),
                        probabilidad=analisis_tmp.get('probabilidad'),
                        recomendaciones=analisis_tmp.get('recomendaciones'),
                        modelo_usado=analisis_tmp.get('modelo_usado', 'RESNET50')
                    )

                    diagnostico = resultado_analisis.enfermedad_detectada
                    diagnostico_numero = analisis_tmp.get('diagnostico_numero')
                    probabilidad = resultado_analisis.probabilidad

                    logger.info(f"ResultadoAnalisis creado al confirmar con ID: {resultado_analisis.id}")

                    request.session['ultimo_analisis_id'] = resultado_analisis.id

                except Exception as e:
                    logger.exception(f"Error al crear análisis al confirmar: {e}")
                    messages.error(request, "Error al confirmar el análisis. Intente nuevamente.")
                    return redirect('core:deteccion_analizar')

            else:
                messages.error(request, "No se encontró un análisis previo para confirmar.")
                return redirect('core:deteccion_analizar')
            
            if diagnostico_numero != 1:
                usuarios_cercanos = encontrar_usuarios_cercanos(plantacion_usuario, radio_km=2)
                
                alertas_enviadas = 0
                for info in usuarios_cercanos:
                    usuario_destino = info['usuario']
                    distancia = info['distancia']
                    
                    AlertaComunitaria.objects.create(
                        usuario_origen=request.user,
                        usuario_destino=usuario_destino,
                        plantacion_origen=plantacion_usuario,
                        enfermedad=diagnostico,
                        distancia=distancia,
                        fecha_alerta=timezone.now()
                    )
                    
                    try:
                        enviar_alerta_email(usuario_destino, request.user, plantacion_usuario, diagnostico, distancia)
                        alertas_enviadas += 1
                    except Exception as e:
                        logger.error(f"Error al enviar email a {usuario_destino.username}: {e}")
                
                logger.info(f"Alertas enviadas a {alertas_enviadas} usuarios cercanos")
                
                if diagnostico_numero == 3:
                    messages.success(request, f'¡ALERTA URGENTE ENVIADA! {alertas_enviadas} usuarios notificados.')
                else:
                    messages.success(request, f'Se enviaron {alertas_enviadas} alertas a la comunidad.')
            else:
                messages.success(request, 'Detección confirmada. Plantación en buen estado.')
            
            context = self.get_context_data(
                deteccion_guardada=True,
                modelo_disponible=True,
                diagnostico=diagnostico,
                diagnostico_numero=diagnostico_numero,
                probabilidad=probabilidad,
                recomendaciones=resultado_analisis.recomendaciones,
                imagen_original={'url': resultado_analisis.imagen.imagen.url}
            )
            
            if 'ultimo_analisis_id' in request.session:
                del request.session['ultimo_analisis_id']
            if 'analisis_tmp' in request.session:
                del request.session['analisis_tmp']
            if 'diagnostico_numero' in request.session:
                del request.session['diagnostico_numero']
            
            return render(request, self.template_name, context)
            
        except ResultadoAnalisis.DoesNotExist:
            logger.error(f"No se encontró ResultadoAnalisis con ID: {analisis_id}")
            messages.error(request, "No se encontró el análisis. Por favor, analice la imagen nuevamente.")
            return redirect('core:deteccion_analizar')
            
        except Exception as e:
            logger.exception(f"Error al confirmar alertas: {e}")
            messages.error(request, f'Error al enviar alertas: {str(e)}')
            return redirect('core:deteccion_analizar')
    
    def analizar_imagen(self, request):
        imagen = request.FILES['imagen']
        nombre_archivo = imagen.name
        
        carpeta_temp = os.path.join(settings.MEDIA_ROOT, 'temp')
        carpeta_resultados = os.path.join(settings.MEDIA_ROOT, 'resultados')
        os.makedirs(carpeta_temp, exist_ok=True)
        os.makedirs(carpeta_resultados, exist_ok=True)
        
        ruta_temp = os.path.join(carpeta_temp, nombre_archivo)
        
        modelo_disponible = False
        diagnostico = None
        diagnostico_numero = None
        probabilidad = None
        recomendaciones = ""
        probabilidades_todas = None
        error_modelo = None
        imagenes_procesadas = []
        imagen_original = None
        
        try:
            with open(ruta_temp, 'wb+') as destino:
                for chunk in imagen.chunks():
                    destino.write(chunk)
            logger.info(f"Imagen guardada temporalmente: {ruta_temp}")
        except Exception as e:
            logger.error(f"Error al guardar imagen temporal: {e}")
            messages.error(request, "No se pudo guardar la imagen. Intente nuevamente.")
            return render(request, self.template_name, self.get_context_data())
        
        nombre_original = f"original_{nombre_archivo}"
        ruta_original_resultado = os.path.join(carpeta_resultados, nombre_original)
        
        try:
            shutil.copy2(ruta_temp, ruta_original_resultado)
            logger.info(f"Imagen original copiada a: {ruta_original_resultado}")
        except Exception as e:
            logger.error(f"Error al copiar imagen original: {e}")
        
        try:
            try:
                logger.info("Iniciando predicción con ResNet50...")
                
                diagnostico_numero, pred_probs, confidence, detailed_results = predict_with_resnet50(ruta_temp)
                
                modelo_disponible = True
                diagnostico = obtener_nombre_enfermedad(diagnostico_numero)
                probabilidad = round(confidence * 100, 2)
                recomendaciones = obtener_recomendaciones(diagnostico_numero)
                probabilidades_todas = detailed_results
                
                logger.info(f"ResNet50 completado: {diagnostico} (clase {diagnostico_numero}) - Confianza: {probabilidad}%")
                messages.success(request, f'Análisis completado: {diagnostico} con {probabilidad}% de confianza')
                
            except Exception as e:
                logger.error(f"Error durante la predicción con ResNet50: {e}")
                error_modelo = str(e)
                messages.error(request, f"Error en el análisis: {str(e)}")
            
            if modelo_disponible:
                logger.info("Iniciando segmentación adaptativa...")
                paths_dict = segment_and_save(image_path=ruta_temp, output_dir=carpeta_resultados)
                logger.info(f"Segmentación completada. Archivos generados: {len(paths_dict)}")
                
                imagen_original = {
                    "nombre": "Imagen Original",
                    "url": settings.MEDIA_URL + 'resultados/' + nombre_original
                }
                
                imagenes_procesadas = [
                    {
                        "nombre": "Contorno de la Enfermedad",
                        "url": settings.MEDIA_URL + 'resultados/' + os.path.basename(paths_dict["contorno"]),
                        "descripcion": "Áreas afectadas delimitadas con contornos"
                    },
                    {
                        "nombre": "Mapa de Calor (Overlay)",
                        "url": settings.MEDIA_URL + 'resultados/' + os.path.basename(paths_dict["overlay"]),
                        "descripcion": "Visualización superpuesta de las zonas afectadas"
                    },
                    {
                        "nombre": "Región Afectada",
                        "url": settings.MEDIA_URL + 'resultados/' + os.path.basename(paths_dict["damage"]),
                        "descripcion": "Solo las áreas con síntomas de la enfermedad"
                    }
                ]
                
                try:
                    nombre_contorno = os.path.basename(paths_dict.get("contorno", ""))
                    nombre_overlay = os.path.basename(paths_dict.get("overlay", ""))
                    nombre_damage = os.path.basename(paths_dict.get("damage", ""))

                    nombre_original_resultado = nombre_original

                    analisis_tmp = {
                        'diagnostico': diagnostico,
                        'diagnostico_numero': diagnostico_numero,
                        'probabilidad': probabilidad,
                        'recomendaciones': recomendaciones,
                        'modelo_usado': 'RESNET50',
                        'imagen_original': f'resultados/{nombre_original_resultado}',
                        'contorno': f'resultados/{nombre_contorno}' if nombre_contorno else None,
                        'overlay': f'resultados/{nombre_overlay}' if nombre_overlay else None,
                        'damage': f'resultados/{nombre_damage}' if nombre_damage else None,
                    }

                    request.session['analisis_tmp'] = analisis_tmp
                    request.session['diagnostico_numero'] = diagnostico_numero

                    logger.info(f"Resultado de análisis guardado temporalmente en sesión")

                except Exception as e:
                    logger.error(f"Error al preparar análisis temporal en sesión: {e}")
                    messages.warning(request, "El análisis se completó pero no se pudo preparar para confirmación.")
        
        except Exception as e:
            logger.exception(f"Error durante el análisis de la imagen: {e}")
            messages.error(request, f"Ocurrió un error durante el análisis: {str(e)}")
            error_modelo = str(e)
        
        finally:
            try:
                if os.path.exists(ruta_temp):
                    os.remove(ruta_temp)
                    logger.info(f"Archivo temporal eliminado: {ruta_temp}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar el archivo temporal: {e}")
        
        context = self.get_context_data(
            modelo_disponible=modelo_disponible,
            diagnostico=diagnostico,
            diagnostico_numero=diagnostico_numero,
            probabilidad=probabilidad,
            recomendaciones=recomendaciones,
            probabilidades_todas=probabilidades_todas,
            error_modelo=error_modelo,
            imagenes=imagenes_procesadas,
            imagen_original=imagen_original,
        )
        
        return render(request, self.template_name, context)


class DeteccionListView(LoginRequiredMixin, ListView):
    model = ResultadoAnalisis
    template_name = 'core/Dashboard/Modulo Deteccion Enfermedades/deteccion_list.html'
    context_object_name = 'detecciones'
    paginate_by = 10

    def get_queryset(self):
        return ResultadoAnalisis.objects.filter(
            imagen__plantacion__usuario=self.request.user
        ).select_related('imagen__plantacion').order_by('-fecha_analisis')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        total = qs.count()
        sanas = qs.filter(enfermedad_detectada__iexact='Banana Healthy Leaf').count()
        context.update({
            'stats_total': total,
            'stats_sanas': sanas,
            'stats_enfermas': total - sanas,
            'stats_alertas': AlertaComunitaria.objects.filter(usuario_destino=self.request.user).count(),
            'stats_ultimo': qs.first(),
        })
        return context


class DetalleAnalisisView(LoginRequiredMixin, View):

    template_name = 'core/Dashboard/Modulo Deteccion Enfermedades/detalle_analisis.html'
    
    def get(self, request, id, *args, **kwargs):
        resultado_analisis = get_object_or_404(ResultadoAnalisis, id=id)
        
        if resultado_analisis.imagen.plantacion.usuario != request.user:
            messages.error(request, "No tiene permisos para ver este análisis.")
            return redirect('core:deteccion_list')
        
        context = {
            'diagnostico': resultado_analisis.enfermedad_detectada,
            'probabilidad': resultado_analisis.probabilidad,
            'recomendaciones': resultado_analisis.recomendaciones,
            'fecha_analisis': resultado_analisis.fecha_analisis,
            'modelo_usado': getattr(resultado_analisis, 'modelo_usado', 'RESNET50'),
            'imagen_url': resultado_analisis.imagen.imagen.url,
            'contorno_url': resultado_analisis.imagen.contorno.url if resultado_analisis.imagen.contorno else None,
            'overlay_url': resultado_analisis.imagen.overlay.url if resultado_analisis.imagen.overlay else None,
            'damage_url': resultado_analisis.imagen.damage.url if resultado_analisis.imagen.damage else None,
            'resultado_id': id
        }
        
        return render(request, self.template_name, context)
