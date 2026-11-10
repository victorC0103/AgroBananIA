from django.shortcuts import get_object_or_404, render

def recomendaciones(request):
    return render(request, 'core/Dashboard/Modulo Recomendaciones/list_recomendaciones.html')
