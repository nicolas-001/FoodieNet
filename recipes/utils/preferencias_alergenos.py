def filtrar_recetas_por_usuario(user, recetas):
    perfil = user.perfil
    preferencias = perfil.preferencias.all()

    # Separar por tipo
    evitar = preferencias.filter(tipo='avoid').values_list('nombre', flat=True)
    alergias = preferencias.filter(tipo='allergy').values_list('nombre', flat=True)

    recetas_filtradas = recetas

    # Excluir recetas que tengan ingredientes que el usuario quiere evitar
    for ingrediente in evitar:
        recetas_filtradas = recetas_filtradas.exclude(ingredientes__icontains=ingrediente)

    # Excluir recetas que tengan ingredientes que causen alergias
    for alergia in alergias:
        recetas_filtradas = recetas_filtradas.exclude(ingredientes__icontains=alergia)

    # Excluir recetas que tengan tags que el usuario quiere evitar
    for tag in evitar:
        recetas_filtradas = recetas_filtradas.exclude(tags__name__icontains=tag)

    return recetas_filtradas