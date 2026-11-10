import math
from django.core.mail import send_mail
from django.conf import settings


def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371 
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distancia = R * c 
    return distancia


def enviar_correo(subject, message, recipient_list):

    send_mail(
        subject, 
        message, 
        settings.EMAIL_HOST_USER,  
        recipient_list,  
        fail_silently=False, 
    )