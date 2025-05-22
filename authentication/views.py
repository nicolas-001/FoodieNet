from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro exitoso. Por favor, inicia sesión.")
            return redirect('authentication:login')  # Aquí redirige a login
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('recipes:recetas')  # Aquí redirige a lista de recetas
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('recipes:recetas')  # Aquí redirige a lista de recetas tras logout