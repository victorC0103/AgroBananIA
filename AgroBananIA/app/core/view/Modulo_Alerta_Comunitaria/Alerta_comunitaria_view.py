from app.core.templatetags.agro_tags import nombre_es
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from app.core.models import AlertaComunitaria, Plantacion
from AgroBananIA.utils.calcular_distancia import calcular_distancia
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
import logging

logger = logging.getLogger(__name__)


class AlertasComunitariasView(LoginRequiredMixin, ListView):

    model = AlertaComunitaria
    template_name = 'core/Dashboard/Modulo Alertas Comunitaria/alert_list.html'
    paginate_by = 15
    context_object_name = 'alertas'

    def get_queryset(self):
        return AlertaComunitaria.objects.filter(
            usuario_destino=self.request.user
        ).select_related(
            'usuario_origen', 'plantacion_origen'
        ).order_by('-fecha_alerta')

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        page_obj = context.get('page_obj')

        def nivel_por_distancia(dist):
            try:
                d = float(dist)
            except Exception:
                return 'BAJA'
            if d <= 1:
                return 'ALTA'
            elif d <= 3:
                return 'MEDIA'
            else:
                return 'BAJA'

        if page_obj and hasattr(page_obj, 'object_list'):
            for alerta in page_obj.object_list:

                if not hasattr(alerta, 'nivel_urgencia') or not getattr(alerta, 'nivel_urgencia'):
                    setattr(alerta, 'nivel_urgencia', nivel_por_distancia(getattr(alerta, 'distancia', 9999)))
                if not hasattr(alerta, 'mensaje') or not getattr(alerta, 'mensaje'):
                    distancia = getattr(alerta, 'distancia', None)
                    distancia_txt = f"{distancia:.1f}".replace('.', ',') if isinstance(distancia, (int, float)) else distancia
                    default_msg = f"{nombre_es(getattr(alerta, 'enfermedad', ''))} detectada a {distancia_txt} km de tu plantación"
                    setattr(alerta, 'mensaje', default_msg)

        return context


def encontrar_usuarios_cercanos(plantacion_origen, radio_km=2):

    usuarios_cercanos = []

    plantaciones = Plantacion.objects.exclude(usuario=plantacion_origen.usuario).filter(
        latitud__isnull=False, longitud__isnull=False
    )

    for plantacion in plantaciones:
        distancia = calcular_distancia(
            float(plantacion_origen.latitud),
            float(plantacion_origen.longitud),
            float(plantacion.latitud),
            float(plantacion.longitud)
        )
        if distancia <= radio_km:
            usuarios_cercanos.append({
                'usuario': plantacion.usuario,
                'plantacion': plantacion,
                'distancia': round(distancia, 2)
            })

    return usuarios_cercanos

def enviar_alerta_email(usuario_destino, usuario_origen, plantacion_origen, enfermedad, distancia):

    try:
        context = {
            'usuario_destino': usuario_destino,
            'usuario_origen': usuario_origen,
            'plantacion_origen': plantacion_origen,
            'enfermedad': enfermedad,
            'distancia': round(distancia, 2),
            'fecha': timezone.now().strftime('%d/%m/%Y'),
            'hora': timezone.now().strftime('%H:%M'),
            'nivel_urgencia': _determinar_nivel_urgencia(distancia),
            'color_urgencia': _obtener_color_urgencia(distancia),
        }
        
        html_content = _generar_contenido_html(context)
        text_content = _generar_contenido_texto(context)
        
        asunto = f'🚨 Alerta BanaIA - {enfermedad} detectada a {distancia:.1f}km'
        
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[usuario_destino.email],
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Alerta enviada exitosamente a {usuario_destino.email}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando alerta a {usuario_destino.email}: {str(e)}")
        return False
    
    

def _determinar_nivel_urgencia(distancia):

    if distancia <= 1:
        return "CRÍTICA"
    elif distancia <= 3:
        return "ALTA"
    elif distancia <= 5:
        return "MEDIA"
    else:
        return "BAJA"

def _obtener_color_urgencia(distancia):
    if distancia <= 1:
        return "#dc2626" 
    elif distancia <= 3:
        return "#ea580c" 
    elif distancia <= 5:
        return "#d97706"  
    else:
        return "#059669"  

def _generar_contenido_html(context):

    return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alerta BanaIA</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            background-color: #f8fafc;
        }}
        .container {{
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            margin: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, {context['color_urgencia']}, {context['color_urgencia']}dd);
            color: white;
            padding: 25px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }}
        .urgency-badge {{
            background-color: rgba(255, 255, 255, 0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin-top: 10px;
        }}
        .content {{
            padding: 30px;
        }}
        .greeting {{
            font-size: 18px;
            color: #1f2937;
            margin-bottom: 20px;
        }}
        .alert-info {{
            background-color: #fef3c7;
            border-left: 4px solid {context['color_urgencia']};
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }}
        .info-item {{
            background-color: #f9fafb;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}
        .info-label {{
            font-weight: 600;
            color: #374151;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .info-value {{
            color: #111827;
            font-size: 16px;
        }}
        .recommendations {{
            background-color: #ecfdf5;
            border: 1px solid #d1fae5;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }}
        .recommendations h3 {{
            color: #065f46;
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .rec-list {{
            list-style: none;
            padding: 0;
        }}
        .rec-list li {{
            padding: 8px 0;
            border-bottom: 1px solid #d1fae5;
            color: #047857;
        }}
        .rec-list li:last-child {{
            border-bottom: none;
        }}
        .rec-list li:before {{
            content: "✓ ";
            color: #10b981;
            font-weight: bold;
        }}
        .footer {{
            background-color: #f3f4f6;
            padding: 20px;
            text-align: center;
            color: #6b7280;
            font-size: 14px;
        }}
        .logo {{
            font-size: 20px;
            font-weight: bold;
            color: #059669;
        }}
        .contact-info {{
            margin-top: 15px;
            font-size: 12px;
        }}
        @media (max-width: 600px) {{
            .info-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Alerta Comunitaria</h1>
            <div class="urgency-badge">URGENCIA {context['nivel_urgencia']}</div>
        </div>
        
        <div class="content">
            <div class="greeting">
                Estimado/a <strong>{context['usuario_destino'].get_full_name() or context['usuario_destino'].username}</strong>,
            </div>
            
            <div class="alert-info">
                <strong>Se ha detectado {context['enfermedad']} en una plantación cercana a la tuya.</strong>
                Esta alerta automática te ayuda a tomar medidas preventivas oportunas.
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">📍 Ubicación Afectada</div>
                    <div class="info-value">{context['plantacion_origen'].nombre_finca}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">🦠 Enfermedad Detectada</div>
                    <div class="info-value">{context['enfermedad']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">📏 Distancia</div>
                    <div class="info-value">{context['distancia']} km</div>
                </div>
                <div class="info-item">
                    <div class="info-label">👤 Reportado por</div>
                    <div class="info-value">{context['usuario_origen'].get_full_name() or context['usuario_origen'].username}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">📅 Fecha y Hora</div>
                    <div class="info-value">{context['fecha']} - {context['hora']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">⚠️ Nivel de Riesgo</div>
                    <div class="info-value" style="color: {context['color_urgencia']}; font-weight: bold;">
                        {context['nivel_urgencia']}
                    </div>
                </div>
            </div>
            
            <div class="recommendations">
                <h3>🔍 Recomendaciones Inmediatas</h3>
                <ul class="rec-list">
                    <li>Inspecciona visualmente tu plantación en busca de síntomas similares</li>
                    <li>Utiliza el sistema de análisis BanaIA para un diagnóstico preciso</li>
                    <li>Implementa medidas de bioseguridad en tu finca</li>
                    <li>Mantente atento a futuros reportes de la zona</li>
                    <li>Contacta a un especialista agrícola si observas síntomas</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <div class="logo">🍌 AgroBananIA</div>
            <div>Inteligencia Artificial para el Cultivo de Banano</div>
            <div class="contact-info">
                Este es un mensaje automático del sistema de alertas comunitarias.<br>
                Para más información, visita nuestra plataforma o contacta soporte técnico.
            </div>
        </div>
    </div>
</body>
</html>
"""

def _generar_contenido_texto(context):

    return f"""
🚨 ALERTA COMUNITARIA AgroBananIA - URGENCIA {context['nivel_urgencia']}

Estimado/a {context['usuario_destino'].get_full_name() or context['usuario_destino'].username},

Se ha detectado {context['enfermedad']} en una plantación cercana a la tuya.

DETALLES DE LA ALERTA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Ubicación: {context['plantacion_origen'].nombre_finca}
🦠 Enfermedad: {context['enfermedad']}
📏 Distancia: {context['distancia']} km de tu plantación
👤 Reportado por: {context['usuario_origen'].get_full_name() or context['usuario_origen'].username}
📅 Fecha: {context['fecha']} - {context['hora']}
⚠️  Nivel de Riesgo: {context['nivel_urgencia']}

RECOMENDACIONES INMEDIATAS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Inspecciona tu plantación visualmente
✓ Utiliza el análisis BanaIA para diagnóstico preciso
✓ Implementa medidas de bioseguridad
✓ Mantente atento a reportes de la zona
✓ Contacta especialista si observas síntomas

Gracias por ser parte de la comunidad agrícola inteligente.

--
🍌 Equipo BanaIA
Inteligencia Artificial para el Cultivo de Banano
"""
def enviar_alertas_masivas(usuarios_cercanos, usuario_origen, plantacion_origen, enfermedad):

    resultados = {
        'enviados': 0,
        'fallidos': 0,
        'errores': []
    }
    
    for usuario_data in usuarios_cercanos:
        usuario = usuario_data['usuario']
        distancia = usuario_data['distancia']
        
        try:
            if enviar_alerta_email(usuario, usuario_origen, plantacion_origen, enfermedad, distancia):
                resultados['enviados'] += 1
            else:
                resultados['fallidos'] += 1
        except Exception as e:
            resultados['fallidos'] += 1
            resultados['errores'].append(f"{usuario.email}: {str(e)}")
    
    logger.info(f"Alertas masivas completadas: {resultados['enviados']} enviados, {resultados['fallidos']} fallidos")
    return resultados

