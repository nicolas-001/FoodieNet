from django import forms
from .models import Receta, Comentario

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
            'tags',  # ¡añádelo aquí!
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
