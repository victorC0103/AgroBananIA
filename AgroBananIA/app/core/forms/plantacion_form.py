# app/core/forms/plantacion_form.py
from django import forms
from app.core.models import Plantacion


class PlantacionForm(forms.ModelForm):
    class Meta:
        model = Plantacion
        fields = ['nombre_finca', 'ubicacion', 'extension_hectareas', 'latitud', 'longitud']
        widgets = {
            'nombre_finca': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ej: Finca El Porvenir'
            }),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-input',
                'id': 'id_ubicacion',
                'placeholder': 'Ej: Vía a Daule, Guayas'
            }),
            'extension_hectareas': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Ej: 50.00'
            }),
            'latitud': forms.HiddenInput(),  # ← Oculto, se actualiza por JS
            'longitud': forms.HiddenInput(),  # ← Oculto, se actualiza por JS
        }
        labels = {
            'nombre_finca': 'Nombre de la Finca',
            'ubicacion': 'Dirección',
            'extension_hectareas': 'Extensión (hectáreas)',
            'latitud': 'Latitud',
            'longitud': 'Longitud',
        }

    def clean(self):
        cleaned_data = super().clean()
        lat = cleaned_data.get('latitud')
        lon = cleaned_data.get('longitud')

        if lat is not None and (lat < -90 or lat > 90):
            self.add_error('latitud', 'La latitud debe estar entre -90 y 90.')
        if lon is not None and (lon < -180 or lon > 180):
            self.add_error('longitud', 'La longitud debe estar entre -180 y 180.')
            
        return cleaned_data
