# authentication/signals.py
from django.dispatch import receiver
from allauth.account.signals import user_signed_up
from django.contrib.auth.models import User
from users.models import Perfil

@receiver(user_signed_up)
def crear_perfil_google(request, user, **kwargs):
    """
    Se ejecuta cuando un usuario se registra usando Google.
    Crea automáticamente un Perfil vacío o con datos de Google si los quieres.
    """
    perfil = Perfil.objects.create(user=user)
    
    # Si quieres, puedes extraer información de Google
    sociallogin = kwargs.get('sociallogin')
    if sociallogin:
        extra_data = sociallogin.account.extra_data
        # Por ejemplo nombre completo
        user.first_name = extra_data.get('given_name', '')
        user.last_name = extra_data.get('family_name', '')
        user.save()
        # Foto de perfil de Google
        foto_url = extra_data.get('picture')
        if foto_url:
            import requests
            from django.core.files.base import ContentFile
            response = requests.get(foto_url)
            if response.status_code == 200:
                perfil.foto.save(f"{user.username}_google.jpg", ContentFile(response.content), save=True)
