from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Receta

@admin.register(Receta)
class RecetaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'fecha_creacion', 'es_publica')
    search_fields = ('titulo', 'autor', 'descripcion')
    list_filter = ('es_publica',)