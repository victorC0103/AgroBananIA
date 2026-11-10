# core/mixins.py
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from app.core.models import Plantacion

class PlantacionRequeridaMixin(LoginRequiredMixin):
    """Mixin que verifica si el usuario tiene plantación"""
    
    def dispatch(self, request, *args, **kwargs):
        if not Plantacion.objects.filter(usuario=request.user).exists():
            return redirect('core:registro_plantacion')
        return super().dispatch(request, *args, **kwargs)
