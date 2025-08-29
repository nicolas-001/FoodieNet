from django import forms
from .models import GrupoRecetas
from recipes.models import Receta

class GrupoForm(forms.ModelForm):
    class Meta:
        model = GrupoRecetas
        fields = ['nombre', 'descripcion', 'privacidad']
        widgets = {
            'privacidad': forms.RadioSelect(attrs={
                'class': 'text-blue-600'
            })
        }
class AñadirRecetaGrupoForm(forms.Form):
    receta = forms.ModelChoiceField(
        queryset=Receta.objects.none(),  # se rellenará en la vista
        label="Selecciona una receta",
        widget=forms.Select(attrs={
            "class": "w-full border border-gray-300 rounded-xl p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
        })
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostrar solo las recetas del usuario logueado
        self.fields['receta'].queryset = Receta.objects.filter(autor=user)
