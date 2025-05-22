from django.shortcuts import get_object_or_404, render, redirect
from .models import Receta
from .forms import RecetaForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
# Create your views here.

def lista_recetas(request):
    recetas = Receta.objects.all()
    return render(request, 'recipes/lista_recetas.html', {'recetas': recetas})

def detalle_receta(request, pk):
    receta = get_object_or_404(Receta, pk=pk)
    return render(request, 'recipes/detalle_receta.html', {'receta': receta})
@login_required
def crear_receta(request):
    if request.method == 'POST':
        form = RecetaForm(request.POST, request.FILES)
        if form.is_valid():
            receta = form.save(commit=False)
            receta.autor = request.user
            receta.save()
            return redirect('detalle_receta', pk=receta.pk)
    else:
        form = RecetaForm()
    return render(request, 'recipes/crear_receta.html', {'form': form})

class EditarRecetaView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Receta
    fields = ['titulo', 'descripcion', 'ingredientes', 'pasos', 'imagen']
    template_name = 'recipes/editar_receta.html'

    def get_success_url(self):
        return reverse_lazy('detalle_receta', kwargs={'pk': self.object.pk})

    def test_func(self):
        receta = self.get_object()
        return receta.autor == self.request.user