from django import forms
from .models import Receta, Comentario,PlanDiario
from django.db import models
from django.utils.safestring import mark_safe


class RecetaForm(forms.ModelForm):
    class Meta:
        model = Receta
        fields = [
            'titulo',
            'descripcion',
            'ingredientes',
            'pasos',
            'imagen',
            'es_publica',
            'tiempo_preparacion',
            'dificultad',
            'porciones',
            'tags',
              # ¡añádelo aquí!
        ]
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'ingredientes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'pasos': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'es_publica': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tiempo_preparacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'dificultad': forms.Select(attrs={'class': 'form-select'}),
            'porciones': forms.NumberInput(attrs={'min': 1}),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: pasta, rápida, vegana',
            }),
        }

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto']
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe un comentario...', 'class': 'form-control'}),
        }
class PlanDiarioForm(forms.ModelForm):
    class Meta:
        model = PlanDiario
        fields = ["nombre", "recetas"]

    recetas = forms.ModelMultipleChoiceField(
        queryset=Receta.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop("usuario", None)
        super().__init__(*args, **kwargs)

        if usuario:
            qs = Receta.objects.filter(models.Q(autor=usuario) | models.Q(es_publica=True)).distinct()
            self.fields["recetas"].queryset = qs

            # Generar etiquetas con calorías por persona y data-attrs
            self.fields["recetas"].label_from_instance = lambda obj: f'{obj.titulo} ({round(obj.calorias_por_persona or 0, 1)} kcal)'
            for receta in qs:
                receta.attrs = {
                    "data-calorias": receta.calorias_por_persona or 0,
                    "data-proteinas": (receta.proteinas / receta.porciones) if receta.porciones else 0,
                    "data-grasas": (receta.grasas / receta.porciones) if receta.porciones else 0,
                    "data-carbohidratos": (receta.carbohidratos / receta.porciones) if receta.porciones else 0,
                }

    def as_p(self):
        """Renderizar checkboxes con data-* para JS"""
        output = ""
        for field in self.visible_fields():
            if field.name == "recetas":
                output += f"<label>{field.label}</label><br>"
                for checkbox in field:
                    receta = checkbox.choice_instance
                    attrs = getattr(receta, "attrs", {})
                    extra = " ".join([f'{k}="{v}"' for k, v in attrs.items()])
                    output += (
                        f'<label>'
                        f'<input type="checkbox" name="{checkbox.data["name"]}" value="{checkbox.data["value"]}" {extra}> '
                        f'{checkbox.choice_label}'
                        f'</label><br>'
                    )
            else:
                output += str(field)
        return mark_safe(output)