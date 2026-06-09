"""Score and transparency constants aligned with score_service (50 + 25 + 25)."""

CAUSE_LABELS = {
    'meio-ambiente': 'Meio ambiente',
    'saude': 'Saúde',
    'educacao': 'Educação',
    'direitos-humanos': 'Direitos humanos',
}

ALLOCATION_CRITERIA = [
    {
        'key': 'cnpj',
        'label': 'CNPJ Ativo e Validado',
        'description': (
            'Verificação automática junto à API pública de CNPJ. '
            'CNPJs com situação ATIVA recebem 50 pontos no score de confiança.'
        ),
        'weight': 50,
        'icon': 'file-check',
    },
    {
        'key': 'address',
        'label': 'Consistência de Endereço',
        'description': (
            'O endereço cadastral é cruzado com a base de CEP oficial (ViaCEP/Correios). '
            'Endereços consistentes recebem 25 pontos adicionais.'
        ),
        'weight': 25,
        'icon': 'map-pin',
    },
    {
        'key': 'years',
        'label': 'Tempo de Atividade (> 5 anos)',
        'description': (
            'ONGs com mais de 5 anos de operação comprovada pela data de abertura do CNPJ '
            'recebem 25 pontos adicionais, totalizando até 100 pontos.'
        ),
        'weight': 25,
        'icon': 'clock',
    },
]
