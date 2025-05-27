from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from users.models import Perfil

class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    foto = forms.ImageField(required=False, label="Foto de perfil")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'foto']

    def save(self, commit=True):
        # 1) Crear el usuario
        user = super().save(commit=commit)
        # 2) Acceder o crear el perfil
        perfil, created = Perfil.objects.get_or_create(user=user)
        # 3) Asignar la foto si viene en el form
        foto = self.cleaned_data.get('foto')
        if foto:
            perfil.foto = foto
            perfil.save()
        return user