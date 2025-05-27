from django import forms
from django.contrib.auth.models import User
from .models import Perfil

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email']
class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto']