from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import GrupoRecetas, GrupoMiembro, RecetaGrupo
from recipes.models import Receta
from .forms import GrupoForm, AñadirRecetaGrupoForm

# 📌 Listar todos los grupos (públicos y privados si eres amigo del creador)
def grupo_list(request):
    grupos = GrupoRecetas.objects.all()
    return render(request, "grupos/grupo_list.html", {"grupos": grupos})


# 📌 Detalle de grupo
@login_required
def grupo_detalle(request, pk):
    grupo = get_object_or_404(GrupoRecetas, pk=pk)
    miembros = GrupoMiembro.objects.filter(grupo=grupo)
    recetas = [rg.receta for rg in RecetaGrupo.objects.filter(grupo=grupo)]

    es_miembro = GrupoMiembro.objects.filter(grupo=grupo, usuario=request.user).exists()

    context = {
        "grupo": grupo,
        "miembros": miembros,
        "recetas": recetas,
        "es_miembro": es_miembro,
    }
    return render(request, "grupos/grupo_detail.html", context)


# 📌 Crear grupo
@login_required
def grupo_crear(request):
    if request.method == "POST":
        form = GrupoForm(request.POST)
        if form.is_valid():
            grupo = form.save(commit=False)
            grupo.creador = request.user
            grupo.save()
            GrupoMiembro.objects.create(grupo=grupo, usuario=request.user)  # creador es miembro
            return redirect("grupos:grupo_detalle", pk=grupo.pk)
    else:
        form = GrupoForm()
    return render(request, "grupos/grupo_form.html", {"form": form})


# 📌 Unirse a grupo
@login_required
def grupo_unirse(request, pk):
    grupo = get_object_or_404(GrupoRecetas, pk=pk)
    GrupoMiembro.objects.get_or_create(grupo=grupo, usuario=request.user)
    return redirect("grupos:grupo_detalle", pk=grupo.pk)


# 📌 Salir de grupo
@login_required
def grupo_salir(request, pk):
    grupo = get_object_or_404(GrupoRecetas, pk=pk)
    GrupoMiembro.objects.filter(grupo=grupo, usuario=request.user).delete()
    return redirect("grupos:grupo_detalle", pk=grupo.pk)


# 📌 Agregar receta al grupo
@login_required
def grupo_agregar_receta(request, pk):
    grupo = get_object_or_404(GrupoRecetas, pk=pk)
    if request.method == "POST":
        receta_id = request.POST.get("receta")
        receta = get_object_or_404(Receta, id=receta_id, autor=request.user)
        RecetaGrupo.objects.get_or_create(grupo=grupo, receta=receta)
        return redirect("grupos:grupo_detalle", pk=grupo.pk)

    recetas_usuario = Receta.objects.filter(autor=request.user)
    return render(
        request,
        "grupos/grupo_add_receta.html",
        {"grupo": grupo, "recetas_usuario": recetas_usuario},
    )
@login_required
def grupo_editar(request, pk):
    grupo = get_object_or_404(GrupoRecetas, pk=pk, creador=request.user)  # solo el creador puede editar
    if request.method == "POST":
        form = GrupoRecetasForm(request.POST, instance=grupo)
        if form.is_valid():
            form.save()
            return redirect("grupos:grupo_detalle", pk=grupo.pk)
    else:
        form = GrupoRecetasForm(instance=grupo)
    return render(request, "grupos/grupo_form.html", {"form": form, "grupo": grupo})

@login_required
def explorar_grupos(request):
    # Grupos que el usuario creó
    grupos_creados = GrupoRecetas.objects.filter(creador=request.user)

    # Grupos donde el usuario es miembro, pero no creador
    grupos_miembros = GrupoRecetas.objects.filter(
        miembros=request.user
    ).exclude(creador=request.user)

    # Grupos públicos que el usuario ni creó ni pertenece
    grupos_publicos = GrupoRecetas.objects.filter(
        privacidad="publico"
    ).exclude(creador=request.user).exclude(miembros=request.user)

    context = {
        "grupos_creados": grupos_creados,
        "grupos_miembros": grupos_miembros,
        "grupos_publicos": grupos_publicos,
    }
    return render(request, "grupos/explorar_grupos.html", context)
@login_required
def grupo_borrar(request, pk):
    grupo = get_object_or_404(GrupoRecetas, pk=pk)
    if grupo.creador != request.user:
        # Evitar que alguien que no sea el creador borre
        return redirect('grupos:explorar_grupos')

    if request.method == 'POST':
        grupo.delete()
        return redirect('grupos:explorar_grupos')

    # Podrías mostrar un template de confirmación
    return render(request, 'grupos/grupo_confirmar_borrar.html', {'grupo': grupo})


