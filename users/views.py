from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from recipes.models import Receta  # Ajusta si tu modelo se llama distinto
from .forms import UserEditForm  # Formulario para editar usuario

@login_required
def perfil(request):
    user = request.user
    recetas = Receta.objects.filter(autor=user)

    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('users:perfil')
    else:
        form = UserEditForm(instance=user)

    return render(request, 'users/perfil.html', {'form': form, 'recetas': recetas})