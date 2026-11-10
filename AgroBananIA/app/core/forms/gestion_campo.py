# forms.py
from django import forms
from app.core.models import RegistroCampo, Plantacion

class RegistroCampoForm(forms.ModelForm):
    class Meta:
        model = RegistroCampo
        fields = [
            'plantacion', 'fecha_registro',
            'temperatura', 'humedad', 'precipitacion',
            'ph_suelo', 'humedad_suelo', 'nitrogeno',
            'actividad_realizada', 'observaciones'
        ]
        widgets = {
            'fecha_registro': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'temperatura': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'humedad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'precipitacion': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ph_suelo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'humedad_suelo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'nitrogeno': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'actividad_realizada': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        if usuario:
            self.fields['plantacion'].queryset = Plantacion.objects.filter(usuario=usuario)
        self.fields['plantacion'].widget.attrs.update({'class': 'form-control', 'required': 'required'})
        self.fields['fecha_registro'].widget.attrs.update({'required': 'required'})
        
        # Marcar campos requeridos
        self.fields['plantacion'].required = True
        self.fields['fecha_registro'].required = True
