from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    foto = forms.ImageField(required=False, label="Foto de perfil")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'foto']

    def save(self, commit=True):
        user = super().save(commit=commit)
        # Guarda temporalmente la imagen en el objeto, sin tocar el modelo Perfil
        user._foto_temp = self.cleaned_data.get('foto')
        return user
