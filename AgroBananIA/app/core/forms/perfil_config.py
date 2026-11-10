from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from app.core.models import PerfilUsuario

class PerfilUsuarioForm(forms.ModelForm):
    # Campos del modelo User
    first_name = forms.CharField(
        max_length=30,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu nombre'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        label='Apellido',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu apellido'
        })
    )
    
    username = forms.CharField(
        max_length=150,
        label='Nombre de usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de usuario único'
        })
    )
    
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    
    # Campos para cambio de contraseña
    password = forms.CharField(
        required=False,
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        })
    )
    
    confirmar_password = forms.CharField(
        required=False,
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repite la contraseña'
        })
    )

    # Campo de imagen
    foto_perfil = forms.ImageField(
        required=False,
        label='Foto de perfil',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = PerfilUsuario
        fields = ['telefono', 'direccion', 'foto_perfil']
        widgets = {
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+593 99 999 9999'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ingresa tu dirección completa'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Llenar campos del modelo User si existe
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['username'].initial = self.user.username
            self.fields['email'].initial = self.user.email

    def clean_username(self):
        username = self.cleaned_data['username']
        if self.user and User.objects.filter(username=username).exclude(id=self.user.id).exists():
            raise ValidationError('Este nombre de usuario ya está en uso.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if self.user and User.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise ValidationError('Este correo electrónico ya está en uso.')
        return email

    def clean_foto_perfil(self):
        foto = self.cleaned_data.get('foto_perfil')
        if foto:
            if foto.size > 5 * 1024 * 1024:
                raise ValidationError('La imagen es demasiado grande. Máximo 5MB.')
            
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if foto.content_type not in allowed_types:
                raise ValidationError('Formato no soportado. Use JPG, PNG o GIF.')
        return foto

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmar_password = cleaned_data.get('confirmar_password')

        if password or confirmar_password:
            if password != confirmar_password:
                raise ValidationError('Las contraseñas no coinciden.')
            if password and len(password) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')

        return cleaned_data
