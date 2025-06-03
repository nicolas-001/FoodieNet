from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email':    forms.EmailInput(attrs={'class': 'form-control'}),
        }

class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto', 'biografia']
        widgets = {
            'biografia': forms.Textarea(attrs={'rows':3, 'class':'form-control'}),
        }
class UserSearchForm(forms.Form):
    """Formulario para buscar usuarios por username."""
    query = forms.CharField(
        label='Buscar usuario',
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Introduce nombre de usuario…'})
    )