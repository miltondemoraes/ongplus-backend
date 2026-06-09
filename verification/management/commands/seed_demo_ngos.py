from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date

from verification.models import NGO, Campaign, Bundle
from financial.models import FinancialRecord
from transparency.models import NGODocument

# CNPJs claramente fictícios — apenas para ambiente de demonstração.
DEMO_NGOS = [
    {
        'name': 'Instituto Mata Viva',
        'cnpj': '10200300000170',
        'description': (
            'Nossa missão é restaurar o equilíbrio ecológico através da biodiversidade urbana. '
            'Transformamos espaços cinzas em pulmões vivos, conectando comunidades à regeneração '
            'ativa da Floresta Amazônica em perímetros municipais.'
        ),
        'focus_area': 'meio-ambiente',
        'city': 'Manaus',
        'state': 'AM',
        'current_score': 100,
        'years_operating': 16,
        'address_valid': True,
        'verification_status': NGO.VerificationStatus.VERIFIED,
        'social_networks': [
            {'platform': 'instagram', 'handle': '@institutomataviva'},
            {'platform': 'facebook', 'handle': '/institutomataviva'},
        ],
    },
    {
        'name': 'Fundação Rio Puro',
        'cnpj': '20300400000181',
        'description': (
            'Projetos de saneamento básico e acesso à água potável em comunidades '
            'ribeirinhas do Norte e Nordeste.'
        ),
        'focus_area': 'saude',
        'city': 'Santarém',
        'state': 'PA',
        'current_score': 75,
        'years_operating': 12,
        'address_valid': True,
        'verification_status': NGO.VerificationStatus.VERIFIED,
        'social_networks': [{'platform': 'instagram', 'handle': '@fundacaoriopuro'}],
    },
    {
        'name': 'Rede Aprender Juntos',
        'cnpj': '30400500000192',
        'description': (
            'Promovemos acesso à educação de qualidade para jovens em situação de '
            'vulnerabilidade através de bolsas e mentoria educacional.'
        ),
        'focus_area': 'educacao',
        'city': 'São Paulo',
        'state': 'SP',
        'current_score': 50,
        'years_operating': 9,
        'address_valid': False,
        'verification_status': NGO.VerificationStatus.ANALYSIS,
        'social_networks': [],
    },
    {
        'name': 'Coletivo Cidadania Ativa',
        'cnpj': '40500600000103',
        'description': (
            'Defesa e fomento dos direitos humanos através de suporte legal, '
            'capacitação e denúncia de violações em áreas periféricas.'
        ),
        'focus_area': 'direitos-humanos',
        'city': 'Rio de Janeiro',
        'state': 'RJ',
        'current_score': 100,
        'years_operating': 14,
        'address_valid': True,
        'verification_status': NGO.VerificationStatus.VERIFIED,
        'social_networks': [
            {'platform': 'instagram', 'handle': '@cidadaniaativa'},
        ],
    },
]

# CNPJs das ONGs de demonstração anteriores — removidos ao reexecutar o seed.
LEGACY_DEMO_CNPJS = [
    '12345678000190',
    '98765432000110',
    '45123890000155',
    '11222333000144',
]


class Command(BaseCommand):
    help = 'Seeds demo NGOs, Campaigns and Bundles for local development'

    def handle(self, *args, **options):
        now = timezone.now()
        ngo_created = 0
        ngo_updated = 0

        removed, _ = NGO.objects.filter(cnpj__in=LEGACY_DEMO_CNPJS).delete()
        if removed:
            self.stdout.write(
                self.style.WARNING(f'Removed {removed} legacy demo NGO record(s).')
            )

        # ── 1. Seed NGOs ─────────────────────────────────────────────────────
        ngo_map = {}
        for data in DEMO_NGOS:
            defaults = {**data, 'is_active': True, 'last_verified_at': now}
            cnpj = data['cnpj']
            ngo, was_created = NGO.objects.update_or_create(
                cnpj=cnpj,
                defaults=defaults,
            )
            ngo_map[data['name']] = ngo
            if was_created:
                ngo_created += 1
            else:
                ngo_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'NGOs ready: {ngo_created} created, {ngo_updated} updated.'
            )
        )

        # ── 2. Seed Campaigns ────────────────────────────────────────────────
        DEMO_CAMPAIGNS = [
            {
                'name': 'Reflorestamento de Nascentes',
                'ngo': ngo_map['Instituto Mata Viva'],
                'description': (
                    'Recuperação direta de 5 nascentes degradadas no entorno urbano de Manaus '
                    'com o plantio planejado de 10 mil mudas de espécies nativas.'
                ),
                'cause': 'meio-ambiente',
                'status': 'publicada',
                'target_amount': 20000,
                'raised_amount': 14200,
                'end_date': date.today() + timedelta(days=12),
                'match_multiplier': 3,
                'match_sponsor': 'BioCorp S.A.',
                'match_cap': 30000.00,
                'match_period': 'Junho a Agosto de 2026',
                'requirements': 'As mudas devem ser apenas de espécies nativas da Amazônia.',
                'destination': 'Compra das mudas e contratação de mão-de-obra local.',
                'location': 'Manaus, AM',
            },
            {
                'name': 'Água Saudável nas Escolas',
                'ngo': ngo_map['Fundação Rio Puro'],
                'description': (
                    'Instalação de filtros de carvão ativo e reservatórios higienizados em '
                    '12 escolas públicas ribeirinhas na região do Baixo Amazonas.'
                ),
                'cause': 'saude',
                'status': 'publicada',
                'target_amount': 35000,
                'raised_amount': 18000,
                'end_date': date.today() + timedelta(days=5),
                'match_multiplier': 1,
                'match_sponsor': None,
                'location': 'Santarém, PA',
            },
            {
                'name': 'Bolsas para Desenvolvedoras',
                'ngo': ngo_map['Rede Aprender Juntos'],
                'description': (
                    'Financiamento completo de cursos intensivos de desenvolvimento de software '
                    'e fornecimento de notebooks para 30 mulheres da periferia paulistana.'
                ),
                'cause': 'educacao',
                'status': 'publicada',
                'target_amount': 50000,
                'raised_amount': 42000,
                'end_date': date.today() + timedelta(days=22),
                'match_multiplier': 2,
                'match_sponsor': 'TechFund Brasil',
                'match_cap': 25000.00,
                'location': 'São Paulo, SP',
            },
        ]

        camp_created = 0
        camp_updated = 0
        for data in DEMO_CAMPAIGNS:
            _, was_created = Campaign.objects.update_or_create(
                name=data['name'],
                ngo=data['ngo'],
                defaults={
                    'description': data['description'],
                    'cause': data['cause'],
                    'status': data.get('status', 'rascunho'),
                    'target_amount': data['target_amount'],
                    'raised_amount': data['raised_amount'],
                    'end_date': data.get('end_date'),
                    'match_multiplier': data['match_multiplier'],
                    'match_sponsor': data['match_sponsor'],
                    'match_cap': data.get('match_cap'),
                    'match_period': data.get('match_period', ''),
                    'requirements': data.get('requirements', ''),
                    'destination': data.get('destination', ''),
                    'location': data['location'],
                    'is_active': True,
                }
            )
            if was_created:
                camp_created += 1
            else:
                camp_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Campaigns ready: {camp_created} created, {camp_updated} updated.'
            )
        )

        # ── 3. Seed Bundles ──────────────────────────────────────────────────
        DEMO_BUNDLES = [
            {
                'name': 'Aliança Amazônia Viva',
                'cause': 'meio-ambiente',
                'description': (
                    'Um esforço conjunto para restaurar áreas degradadas, combater queimadas e '
                    'capacitar comunidades tradicionais na bioeconomia florestal. Unindo a expertise '
                    'de organizações líderes em conservação ativa.'
                ),
                'target_amount': 150000,
                'raised_amount': 98400,
                'match_multiplier': 3,
                'match_sponsor': 'Fundação Clima Global',
                'eligibility_rules': [
                    'Atuação comprovada de no mínimo 3 anos na Bacia Amazônica.',
                    'Score de transparência na plataforma superior a 90/100.',
                    'Apresentação de relatórios trimestrais de impacto socioambiental.',
                    'Adesão ao código de ética e conduta da plataforma ONG+.',
                ],
                'distribution_rules': (
                    'Os recursos deste bundle são distribuídos de forma paritária (50% para cada ONG '
                    'participante). Os repasses ocorrem mensalmente sob condição de entrega das '
                    'prestações de contas parciais e relatórios de atividades.'
                ),
                'ngo_names': ['Instituto Mata Viva', 'Fundação Rio Puro'],
            },
            {
                'name': 'Futuro Brilhante',
                'cause': 'educacao',
                'description': (
                    'Fundo coletivo destinado a equipar escolas comunitárias de periferias com '
                    'laboratórios de informática, além de oferecer bolsas de estudos de programação '
                    'para jovens talentos.'
                ),
                'target_amount': 80000,
                'raised_amount': 32000,
                'match_multiplier': 1,
                'match_sponsor': None,
                'eligibility_rules': [
                    'Foco direto em educação básica ou capacitação tecnológica profissional.',
                    'Score de transparência na plataforma superior a 85/100.',
                    'Demonstração financeira anual auditada externamente.',
                ],
                'distribution_rules': (
                    'A distribuição é proporcional ao score de transparência das organizações '
                    'participantes, otimizando o repasse em favor da excelência na prestação de contas.'
                ),
                'ngo_names': ['Rede Aprender Juntos', 'Coletivo Cidadania Ativa'],
            },
        ]

        bundle_created = 0
        bundle_updated = 0
        for data in DEMO_BUNDLES:
            ngo_names = data.pop('ngo_names')
            bundle, was_created = Bundle.objects.update_or_create(
                name=data['name'],
                defaults={**data, 'is_active': True},
            )
            bundle.ngos.set([ngo_map[n] for n in ngo_names if n in ngo_map])
            if was_created:
                bundle_created += 1
            else:
                bundle_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Bundles ready: {bundle_created} created, {bundle_updated} updated.'
            )
        )

        # ── 4. Seed FinancialRecords (Transfers & Donations) ─────────────────
        now = timezone.now()

        DEMO_RECORDS = [
            {
                'ong': ngo_map['Instituto Mata Viva'],
                'record_type': FinancialRecord.RecordType.TRANSFER,
                'amount': 45000,
                'description': 'Repasse mensal — Reflorestamento de Nascentes',
                'reference_id': 'TRF-001',
                'days_ago': 2,
            },
            {
                'ong': ngo_map['Fundação Rio Puro'],
                'record_type': FinancialRecord.RecordType.TRANSFER,
                'amount': 28000,
                'description': 'Repasse mensal — Água Saudável nas Escolas',
                'reference_id': 'TRF-002',
                'days_ago': 5,
            },
            {
                'ong': ngo_map['Rede Aprender Juntos'],
                'record_type': FinancialRecord.RecordType.TRANSFER,
                'amount': 35000,
                'description': 'Repasse — Bolsas para Desenvolvedoras',
                'reference_id': 'TRF-003',
                'days_ago': 12,
            },
            {
                'ong': ngo_map['Coletivo Cidadania Ativa'],
                'record_type': FinancialRecord.RecordType.TRANSFER,
                'amount': 60000,
                'description': 'Repasse — Suporte Jurídico Comunitário',
                'reference_id': 'TRF-004',
                'days_ago': 20,
            },
            {
                'ong': ngo_map['Instituto Mata Viva'],
                'record_type': FinancialRecord.RecordType.TRANSFER,
                'amount': 22000,
                'description': 'Repasse complementar — Fundo Amazônia Viva',
                'reference_id': 'TRF-005',
                'days_ago': 25,
            },
            {
                'ong': ngo_map['Instituto Mata Viva'],
                'record_type': FinancialRecord.RecordType.DONATION,
                'amount': 98400,
                'description': 'Arrecadação acumulada — Aliança Amazônia Viva',
                'reference_id': 'DON-001',
                'days_ago': 30,
            },
            {
                'ong': ngo_map['Fundação Rio Puro'],
                'record_type': FinancialRecord.RecordType.DONATION,
                'amount': 42000,
                'description': 'Arrecadação acumulada — Água Saudável',
                'reference_id': 'DON-002',
                'days_ago': 30,
            },
            {
                'ong': ngo_map['Rede Aprender Juntos'],
                'record_type': FinancialRecord.RecordType.DONATION,
                'amount': 74000,
                'description': 'Arrecadação acumulada — Futuro Brilhante',
                'reference_id': 'DON-003',
                'days_ago': 30,
            },
            {
                'ong': ngo_map['Coletivo Cidadania Ativa'],
                'record_type': FinancialRecord.RecordType.DONATION,
                'amount': 85000,
                'description': 'Arrecadação acumulada — Coletivo Cidadania Ativa',
                'reference_id': 'DON-004',
                'days_ago': 30,
            },
        ]

        rec_created = 0
        for data in DEMO_RECORDS:
            days_ago = data.pop('days_ago')
            ref_id = data['reference_id']
            created_at = now - timedelta(days=days_ago)
            if not FinancialRecord.objects.filter(reference_id=ref_id).exists():
                obj = FinancialRecord.objects.create(**data)
                FinancialRecord.objects.filter(pk=obj.pk).update(created_at=created_at)
                rec_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'FinancialRecords ready: {rec_created} created.'
            )
        )

        # ── 5. Seed Documents ────────────────────────────────────────────────
        DEMO_DOCUMENTS = [
            {
                'ong': ngo_map['Instituto Mata Viva'],
                'title': 'Relatório de Atividades 2025',
                'description': 'Resumo das atividades e impacto socioambiental do último ano.',
                'document_url': 'https://example.com/relatorio-2025.pdf',
                'is_public': True,
            },
            {
                'ong': ngo_map['Instituto Mata Viva'],
                'title': 'Estatuto Social',
                'description': 'Estatuto social consolidado da organização.',
                'document_url': 'https://example.com/estatuto-imv.pdf',
                'is_public': True,
            },
            {
                'ong': ngo_map['Fundação Rio Puro'],
                'title': 'Auditoria Financeira 2025',
                'description': 'Parecer dos auditores independentes sobre as demonstrações contábeis.',
                'document_url': 'https://example.com/auditoria-2025.pdf',
                'is_public': True,
            }
        ]

        doc_created = 0
        for data in DEMO_DOCUMENTS:
            if not NGODocument.objects.filter(ong=data['ong'], title=data['title']).exists():
                NGODocument.objects.create(**data)
                doc_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'NGODocuments ready: {doc_created} created.'
            )
        )
