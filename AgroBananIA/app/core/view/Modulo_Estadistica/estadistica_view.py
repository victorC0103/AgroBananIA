
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q, Max, Min, Sum
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
import json
from app.core.models import (
    Plantacion, ImagenAnalisis, ResultadoAnalisis, 
    RegistroCampo
)

@login_required
def estadisticas_view(request):
 
    
    user = request.user
    
    plantaciones = Plantacion.objects.filter(usuario=user)
    
  
    total_plantaciones = plantaciones.count()
    total_analisis = ImagenAnalisis.objects.filter(plantacion__usuario=user).count()
    total_registros_campo = RegistroCampo.objects.filter(plantacion__usuario=user).count()
    
 
    enfermedades_stats = ResultadoAnalisis.objects.filter(
        imagen__plantacion__usuario=user
    ).values('enfermedad_detectada').annotate(
        count=Count('enfermedad_detectada'),
        probabilidad_promedio=Avg('probabilidad')
    ).order_by('-count')
    
    
    estadisticas_enfermedades = []
    for enfermedad in enfermedades_stats:
        if enfermedad['enfermedad_detectada']:      
            estadisticas_enfermedades.append({
                'enfermedad': enfermedad['enfermedad_detectada'],
                'count': enfermedad['count'],
                'probabilidad_promedio': round(enfermedad['probabilidad_promedio'], 2) if enfermedad['probabilidad_promedio'] else 0
            })
    

    plantaciones_stats = plantaciones.aggregate(
        total_hectareas=Sum('extension_hectareas'),
        promedio_hectareas=Avg('extension_hectareas'),
        max_hectareas=Max('extension_hectareas'),
        min_hectareas=Min('extension_hectareas')
    )
    
    fecha_inicio = timezone.now() - timedelta(days=30)
    analisis_recientes = ImagenAnalisis.objects.filter(
        plantacion__usuario=user,
        fecha_envio__gte=fecha_inicio
    ).count()
    
    condiciones_climaticas = RegistroCampo.objects.filter(
        plantacion__usuario=user
    ).aggregate(
        temp_promedio=Avg('temperatura'),
        humedad_promedio=Avg('humedad'),
        ph_promedio=Avg('ph_suelo'),
        precipitacion_total=Sum('precipitacion')
    )
    
    casos_criticos = ResultadoAnalisis.objects.filter(
        imagen__plantacion__usuario=user,
        probabilidad__gte=80
    ).count()
    
    analisis_exitosos = ResultadoAnalisis.objects.filter(
        imagen__plantacion__usuario=user
    ).count()
    eficiencia = (analisis_exitosos / total_analisis * 100) if total_analisis > 0 else 0
    
 
    stats_por_plantacion = []
    for plantacion in plantaciones:
        analisis_count = ImagenAnalisis.objects.filter(plantacion=plantacion).count()
        registros_count = RegistroCampo.objects.filter(plantacion=plantacion).count()
        

        ultimo_resultado = ResultadoAnalisis.objects.filter(
            imagen__plantacion=plantacion
        ).order_by('-fecha_analisis').first()
        
        stats_por_plantacion.append({
            'nombre': plantacion.nombre_finca,
            'ubicacion': plantacion.ubicacion,
            'hectareas': float(plantacion.extension_hectareas),
            'analisis_realizados': analisis_count,
            'registros_campo': registros_count,
            'ultima_enfermedad': ultimo_resultado.enfermedad_detectada if ultimo_resultado else 'N/A',
            'probabilidad_ultima': ultimo_resultado.probabilidad if ultimo_resultado else 0
        })
    
    tendencias_mensuales = []
    for i in range(6):
        fecha_mes = timezone.now() - timedelta(days=30*i)
        inicio_mes = fecha_mes.replace(day=1)
        fin_mes = (inicio_mes + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        analisis_mes = ImagenAnalisis.objects.filter(
            plantacion__usuario=user,
            fecha_envio__range=[inicio_mes, fin_mes]
        ).count()
        
        tendencias_mensuales.insert(0, {
            'mes': fecha_mes.strftime('%B %Y'),
            'analisis': analisis_mes
        })

    context = {
        'total_plantaciones': total_plantaciones,
        'total_analisis': total_analisis,
        'total_registros': total_registros_campo,
        'analisis_recientes': analisis_recientes,
        'casos_criticos': casos_criticos,
        'eficiencia': round(eficiencia, 1),
        'estadisticas': json.dumps(estadisticas_enfermedades) if estadisticas_enfermedades else '[]',
        'stats_plantaciones': stats_por_plantacion,
        'condiciones_climaticas': condiciones_climaticas,
        'plantaciones_stats': plantaciones_stats,
        'tendencias_mensuales': json.dumps(tendencias_mensuales) if tendencias_mensuales else '[]',
        'enfermedades_unicas': len(estadisticas_enfermedades),
    }
    


    return render(request, 'core/Dashboard/Modulo Estadisticas/estadistica_list.html', context)

