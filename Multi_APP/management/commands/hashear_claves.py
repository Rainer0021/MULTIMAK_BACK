from django.contrib.auth.hashers import identify_hasher
from django.core.management.base import BaseCommand

from Multi_APP.models import Usuarios


class Command(BaseCommand):
    help = 'Cifra las contraseñas que todavía están guardadas en texto plano en la tabla Usuarios.'

    def add_arguments(self, parser):
        parser.add_argument('--simular', action='store_true', help='Solo cuenta, no modifica nada.')

    def handle(self, *args, **opciones):
        pendientes = 0
        for u in Usuarios.objects.all():
            try:
                identify_hasher(u.contraseña)
                continue 
            except ValueError:
                pass
            pendientes += 1
            if not opciones['simular']:
                u.set_password(u.contraseña)
                u.save(update_fields=['contraseña'])
        accion = 'por cifrar' if opciones['simular'] else 'cifradas'
        self.stdout.write(self.style.SUCCESS(f'Contraseñas {accion}: {pendientes}'))