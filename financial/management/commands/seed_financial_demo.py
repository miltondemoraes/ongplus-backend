from decimal import Decimal

from django.core.management.base import BaseCommand
from authentication.models import CustomUser, DonorProfile
from financial.models import Donation, PaymentMethod
from verification.models import NGO


class Command(BaseCommand):
    help = 'Cria métodos de pagamento, vincula ong@dev.com e doações demo para desenvolvimento local'

    def handle(self, *args, **options):
        methods = [
            ('pix', 'PIX'),
        ]
        method_map = {}
        for method_type, name in methods:
            pm, created = PaymentMethod.objects.get_or_create(
                method_type=method_type,
                name=name,
                defaults={'description': f'Pagamento via {name}', 'is_active': True},
            )
            method_map[method_type] = pm
            action = 'criado' if created else 'já existe'
            self.stdout.write(self.style.SUCCESS(f'Método {name}: {action}'))

        ong_user = CustomUser.objects.filter(email='ong@dev.com').first()
        demo_ngo = NGO.objects.filter(name='Instituto Mata Viva').first()
        if ong_user and demo_ngo:
            if demo_ngo.user_id != ong_user.id:
                demo_ngo.user = ong_user
                demo_ngo.save(update_fields=['user'])
                self.stdout.write(self.style.SUCCESS('ong@dev.com vinculado ao Instituto Mata Viva'))
            else:
                self.stdout.write(self.style.WARNING('ong@dev.com já vinculado ao Instituto Mata Viva'))
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Execute seed_users e seed_demo_ngos antes de seed_financial_demo'
                )
            )

        donor = CustomUser.objects.filter(email='doador@dev.com').first()
        if donor:
            profile, _ = DonorProfile.objects.get_or_create(user=donor)
            if not profile.preferred_causes:
                profile.preferred_causes = ['meio-ambiente', 'educacao']
                profile.save(update_fields=['preferred_causes'])
                self.stdout.write(self.style.SUCCESS('Preferências de causa do doador demo configuradas'))

            if demo_ngo and not Donation.objects.filter(
                donor=donor, ong=demo_ngo, status=Donation.Status.COMPLETED
            ).exists():
                donation = Donation.objects.create(
                    donor=donor,
                    ong=demo_ngo,
                    amount=Decimal('150.00'),
                    payment_method=method_map['pix'],
                    status=Donation.Status.COMPLETED,
                    recurrence_type=Donation.RecurrenceType.ONCE,
                )
                self.stdout.write(self.style.SUCCESS(f'Doação demo criada: {donation.id}'))
            else:
                self.stdout.write(self.style.WARNING('Doação demo do doador já existe ou ONG ausente'))

        self.stdout.write(self.style.SUCCESS('seed_financial_demo concluído'))
