from django.core.management.base import BaseCommand
from users.models import Perfil

class Command(BaseCommand):
    help = 'Poner la foto de perfil por defecto en los perfiles que no tengan foto'

    def handle(self, *args, **kwargs):
        perfiles_sin_foto = Perfil.objects.filter(foto='')  # Filtra perfiles sin foto
        total = perfiles_sin_foto.count()

        if total == 0:
            self.stdout.write('Todos los perfiles ya tienen foto.')
            return

        for perfil in perfiles_sin_foto:
            perfil.foto = 'perfiles/default.jpeg'
            perfil.save()
            self.stdout.write(f'Foto por defecto puesta en perfil de {perfil.user.username}')

        self.stdout.write(self.style.SUCCESS(f'Actualizados {total} perfiles con foto por defecto.'))
