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
    recetas = forms.ModelMultipleChoiceField(
        queryset=Receta.objects.none(),
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = PlanDiario
        fields = ['nombre', 'recetas']

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        if usuario:
            self.fields['recetas'].queryset = Receta.objects.all()