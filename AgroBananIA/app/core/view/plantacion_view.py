
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from app.core.forms.plantacion_form import PlantacionForm
from app.core.models import Plantacion
import requests


def plantacion_requerida(view_func):

    @login_required
    def wrapper(request, *args, **kwargs):
        if not Plantacion.objects.filter(usuario=request.user).exists():
            return redirect('core:registro_plantacion')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def verificar_plantacion(request):
    tiene_plantacion = Plantacion.objects.filter(usuario=request.user).exists()
    if tiene_plantacion:
        return redirect('core:dashboard')   
    else:
        return redirect('core:registro_plantacion')


@login_required
def registro_plantacion(request):

    if Plantacion.objects.filter(usuario=request.user).exists():
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = PlantacionForm(request.POST)
        if form.is_valid():
            plantacion = form.save(commit=False)
            plantacion.usuario = request.user
            plantacion.save()
            return redirect('core:dashboard')
        else:
            print("Errores del formulario:", form.errors) 
    else:
        form = PlantacionForm()

    context = {
        'form': form
    }
    
    return render(request, 'core/plantaciones/registro_plantacion.html', context)


def obtener_direccion(request):

    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    if not lat or not lon:
        return JsonResponse({'error': 'Faltan coordenadas'}, status=400)

    url = 'https://nominatim.openstreetmap.org/reverse'
    params = {
        'lat': lat,
        'lon': lon,
        'format': 'json',
        'addressdetails': 1,
        'zoom': 18,
        'language': 'es'  
    }
    headers = {
        'User-Agent': 'AgroBananIA/1.0 (contact@agrobanania.tech)'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()  
        data = response.json()
        return JsonResponse({
            'direccion': data.get('display_name', 'Dirección no encontrada')
        })
    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'Timeout en la solicitud'}, status=500)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Error al conectar: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
