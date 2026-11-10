from django.contrib import messages
from django.core.cache import cache
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from app.core.models import Plantacion, RegistroCampo
from app.core.forms.gestion_campo import RegistroCampoForm
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
import os
import requests


class GestionCampoListView(LoginRequiredMixin, ListView):
    model = RegistroCampo
    template_name = 'core/Dashboard/Modulo Gestion Campo/gestion_campo.html'
    context_object_name = 'registros_campo'
    paginate_by = 5
    login_url = 'login'
    
    def get_queryset(self):

        return RegistroCampo.objects.filter(
            plantacion__usuario=self.request.user
        ).select_related(
            'plantacion'
        ).order_by('-fecha_registro')
    
    def get_clima_data(self):

        cache_key = f'clima_data_{self.request.user.id}'
        clima = cache.get(cache_key)
        
        if clima:
            return clima

        plantacion = Plantacion.objects.filter(
            usuario=self.request.user
        ).only('latitud', 'longitud').first()
        

        clima = {
            'ciudad': 'No disponible',
            'region': '--',
            'pais': '--',
            'temperatura_c': '--',
            'condicion': 'Sin datos',
            'icono': '',
            'humedad': '--',
            'viento_kph': '--',
            'error': None
        }
        
        if not plantacion:
            clima['error'] = 'No tienes plantaciones registradas'
            return clima
        
        if not plantacion.latitud or not plantacion.longitud:
            clima['error'] = 'No hay coordenadas registradas en la plantación'
            return clima
        
        try:

            api_key = os.getenv('THE_WEATHER_API_KEY')
            lat = plantacion.latitud
            lon = plantacion.longitud
            
            url = f'http://api.weatherapi.com/v1/current.json'
            params = {
                'key': api_key,
                'q': f'{lat},{lon}',
                'lang': 'es'
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            clima = {
                'ciudad': data['location']['name'],
                'region': data['location']['region'],
                'pais': data['location']['country'],
                'temperatura_c': round(data['current']['temp_c'], 1),
                'condicion': data['current']['condition']['text'],
                'icono': data['current']['condition']['icon'],
                'humedad': data['current']['humidity'],
                'viento_kph': round(data['current']['wind_kph'], 1),
                'error': None
            }
            
            cache.set(cache_key, clima, 300)
            
        except requests.exceptions.Timeout:
            clima['error'] = 'Tiempo de espera agotado al obtener el clima'
        except requests.exceptions.RequestException as e:
            clima['error'] = f'Error de conexión: {str(e)}'
        except KeyError as e:
            clima['error'] = f'Error en los datos recibidos: {str(e)}'
        except Exception as e:
            clima['error'] = f'Error inesperado: {str(e)}'
        
        return clima
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        
        context['clima'] = self.get_clima_data()
        
        context['total_registros'] = self.get_queryset().count()

        context['usuario'] = self.request.user
        
        return context
    

class RegistroCampoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = RegistroCampo
    form_class = RegistroCampoForm
    template_name = 'core/Dashboard/Modulo Gestion Campo/registrocampo_form.html'
    success_url = reverse_lazy('core:gestion_campo')
    success_message = '✅ Registro de campo guardado correctamente.'
    login_url = 'login'
    
    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def get_clima_data(self, plantacion):

        cache_key = f'clima_create_{plantacion.id}'
        clima_data = cache.get(cache_key)
        
        if clima_data:
            return clima_data
        
        if not plantacion.latitud or not plantacion.longitud:
            return {}
        
        try:
            lat = plantacion.latitud
            lon = plantacion.longitud
            api_key = os.getenv('THE_WEATHER_API_KEY')
            
            url = 'http://api.weatherapi.com/v1/current.json'
            params = {
                'key': api_key,
                'q': f'{lat},{lon}',
                'lang': 'es'
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            clima = response.json()
            clima_data = {
                'temperatura': round(clima['current']['temp_c'], 1),
                'humedad': clima['current']['humidity'],
                'precipitacion': round(clima['current']['precip_mm'], 2),
            }
            

            cache.set(cache_key, clima_data, 300)
            
            return clima_data
            
        except requests.exceptions.RequestException as e:
            messages.warning(
                self.request, 
                f'⚠️ No se pudo obtener datos climáticos automáticamente: {str(e)}'
            )
            return {}
        except (KeyError, ValueError) as e:
            messages.warning(
                self.request,
                '⚠️ Error al procesar datos climáticos. Complete manualmente.'
            )
            return {}
    
    def get_initial(self):
 
        initial = super().get_initial()
        

        plantacion = Plantacion.objects.filter(
            usuario=self.request.user
        ).first()
        
        if plantacion:

            initial['plantacion'] = plantacion

            clima_data = self.get_clima_data(plantacion)
            initial.update(clima_data)
        
        return initial
    
    def form_valid(self, form):

        return super().form_valid(form)
    
    def form_invalid(self, form):
 
        messages.error(
            self.request,
            '❌ Error al guardar el registro. Por favor, revise los campos.'
        )
        return super().form_invalid(form)


class RegistroCampoUpdateView(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, UpdateView):

    model = RegistroCampo
    form_class = RegistroCampoForm
    template_name = 'core/Dashboard/Modulo Gestion Campo/registrocampo_form.html'
    success_url = reverse_lazy('core:gestion_campo')
    success_message = '✅ Registro actualizado correctamente.'
    login_url = 'login'
    context_object_name = 'registro'
    
    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()
        kwargs['usuario'] = self.request.user
        return kwargs
    
    def get_queryset(self):

        return RegistroCampo.objects.filter(
            plantacion__usuario=self.request.user
        ).select_related('plantacion')
    
    def test_func(self):

        registro = self.get_object()
        return registro.plantacion.usuario == self.request.user
    
    def handle_no_permission(self):

        messages.error(
            self.request,
            '❌ No tienes permisos para editar este registro.'
        )
        return HttpResponseRedirect(reverse_lazy('core:gestion_campo'))
    
    def form_invalid(self, form):

        messages.error(
            self.request,
            '❌ Error al actualizar el registro. Verifique los datos ingresados.'
        )
        return super().form_invalid(form)


class RegistroCampoDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):

    model = RegistroCampo
    template_name = 'core/Dashboard/Modulo Gestion Campo/registrocampo_confirm_delete.html'
    success_url = reverse_lazy('core:gestion_campo')
    login_url = 'login'
    context_object_name = 'registro'
    
    def get_queryset(self):

        return RegistroCampo.objects.filter(
            plantacion__usuario=self.request.user
        ).select_related('plantacion')
    
    def test_func(self):

        registro = self.get_object()
        return registro.plantacion.usuario == self.request.user
    
    def handle_no_permission(self):
    
        messages.error(
            self.request,
            '❌ No tienes permisos para eliminar este registro.'
        )
        return HttpResponseRedirect(reverse_lazy('core:gestion_campo'))
    
    def post(self, request, *args, **kwargs):

        try:
            messages.success(
                request,
                '🗑️ Registro eliminado correctamente.'
            )
            return self.delete(request, *args, **kwargs)
        except Exception as e:
            messages.error(
                request,
                f'❌ Error al eliminar el registro: {str(e)}'
            )
            return HttpResponseRedirect(self.success_url)
    
    def get(self, request, *args, **kwargs):

        return self.post(request, *args, **kwargs)