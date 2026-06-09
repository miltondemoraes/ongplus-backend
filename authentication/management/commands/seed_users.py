from django.core.management.base import BaseCommand

from authentication.models import CustomUser


class Command(BaseCommand):
    help = 'Cria usuários de teste para cada perfil (desenvolvimento local)'

    def handle(self, *args, **options):
        usuarios = [
            {
                'email': 'doador@dev.com',
                'full_name': 'Doador Teste',
                'role': 'donor',
                'password': 'Dev@1234',
            },
            {
                'email': 'ong@dev.com',
                'full_name': 'ONG Teste',
                'role': 'ong',
                'password': 'Dev@1234',
            },
            {
                'email': 'admin@dev.com',
                'full_name': 'Admin Teste',
                'role': 'admin',
                'password': 'Dev@1234',
                'is_staff': True,
                'is_superuser': True,
            },
        ]

        for dados in usuarios:
            email = dados.pop('email')
            password = dados.pop('password')
            if not CustomUser.objects.filter(email=email).exists():
                CustomUser.objects.create_user(email=email, password=password, **dados)
                self.stdout.write(self.style.SUCCESS(f'Usuário criado: {email}'))
            else:
                self.stdout.write(self.style.WARNING(f'Já existe: {email}'))
