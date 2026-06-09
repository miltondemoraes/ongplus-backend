from datetime import date
from verification.constants import ALLOCATION_CRITERIA, CAUSE_LABELS
from verification.models import NGO, Campaign, Bundle


def _format_cnpj(cnpj: str) -> str:
    digits = ''.join(filter(str.isdigit, str(cnpj)))
    if len(digits) != 14:
        return cnpj
    return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}'


def _social_links(social_networks) -> dict:
    if not social_networks:
        return {}
    if isinstance(social_networks, dict):
        return social_networks
    links = {}
    for entry in social_networks:
        if isinstance(entry, dict):
            platform = entry.get('platform')
            handle = entry.get('handle') or entry.get('url', '')
            if platform:
                links[platform] = handle
    return links


def _consistency_status(ngo: NGO) -> str:
    if not ngo.is_active:
        return 'inconsistent'
    if ngo.address_valid:
        return 'consistent'
    return 'warning'


def _build_evidence_list(ngo: NGO) -> list:
    return [
        {
            'label': 'CNPJ ativo na Receita Federal',
            'status': 'success' if ngo.is_active else 'warning',
        },
        {
            'label': 'Endereço validado via API de CEP',
            'status': 'success' if ngo.address_valid else 'warning',
        },
        {
            'label': 'Mais de 5 anos de atuação',
            'status': 'success' if ngo.years_operating > 5 else 'warning',
        },
    ]


def _score_int(ngo: NGO) -> int:
    if ngo.current_score is None:
        return 0
    return int(float(ngo.current_score))


def _location(ngo: NGO) -> str:
    if ngo.city and ngo.state:
        return f'{ngo.city}, {ngo.state}'
    if ngo.city:
        return ngo.city
    if ngo.state:
        return ngo.state
    return ''


def build_verification_payload(ngo: NGO) -> dict:
    score = _score_int(ngo)
    verified_at = ngo.last_verified_at or ngo.updated_at
    last_update = ngo.updated_at

    return {
        'status': ngo.verification_status,
        'verifiedAt': verified_at.isoformat() if verified_at else None,
        'lastUpdate': last_update.isoformat() if last_update else None,
        'consistencyStatus': _consistency_status(ngo),
        'auditStatus': 'monitoring',
        'evidenceList': _build_evidence_list(ngo),
        'criteria': {
            'score': score,
            'yearsActive': ngo.years_operating,
            'addressConsistency': ngo.address_valid,
            'cnpjValidated': ngo.is_active,
            'documentationComplete': ngo.is_active and ngo.address_valid,
        },
    }


def serialize_ngo_list_item(ngo: NGO) -> dict:
    score = _score_int(ngo)
    cause = ngo.focus_area or ''
    return {
        'id': str(ngo.id),
        'name': ngo.name,
        'cnpj': _format_cnpj(ngo.cnpj),
        'description': ngo.description or '',
        'cause': cause,
        'causeLabel': CAUSE_LABELS.get(cause, cause.replace('-', ' ').title()),
        'score': score,
        'location': _location(ngo),
        'verified': ngo.verification_status == NGO.VerificationStatus.VERIFIED,
        'scoreUpdatedAt': ngo.last_verified_at.isoformat() if ngo.last_verified_at else None,
    }


def serialize_ngo_detail(ngo: NGO) -> dict:
    base = serialize_ngo_list_item(ngo)
    base.update({
        'city': ngo.city or '',
        'state': ngo.state or '',
        'socialLinks': _social_links(ngo.social_networks),
        'yearsOperating': ngo.years_operating,
        'lastUpdated': (
            ngo.last_verified_at.strftime('%d/%m/%Y')
            if ngo.last_verified_at
            else ngo.updated_at.strftime('%d/%m/%Y')
        ),
        'lastExternalAudit': ngo.last_external_audit.strftime('%b %Y').title() if ngo.last_external_audit else None,
        'verification': build_verification_payload(ngo),
    })
    return base


def get_allocation_criteria() -> list:
    return ALLOCATION_CRITERIA


def serialize_campaign(campaign: Campaign) -> dict:
    cause = campaign.cause or ''
    ngo = campaign.ngo
    return {
        'id': str(campaign.id),
        'name': campaign.name,
        'ngoId': str(ngo.id),
        'ngoName': ngo.name,
        'description': campaign.description or '',
        'cause': cause,
        'causeLabel': CAUSE_LABELS.get(cause, cause.replace('-', ' ').title()),
        'targetAmount': float(campaign.target_amount),
        'raisedAmount': float(campaign.raised_amount),
        'status': campaign.status,
        'endDate': campaign.end_date.isoformat() if campaign.end_date else None,
        'daysLeft': max((campaign.end_date - date.today()).days, 0) if campaign.end_date else 0,
        'matchMultiplier': campaign.match_multiplier,
        'matchSponsor': campaign.match_sponsor,
        'matchCap': float(campaign.match_cap) if campaign.match_cap else None,
        'matchPeriod': campaign.match_period,
        'requirements': campaign.requirements,
        'destination': campaign.destination,
        'location': campaign.location or '',
        'score': _score_int(ngo),
    }


def serialize_bundle_list_item(bundle: Bundle) -> dict:
    cause = bundle.cause or ''
    ngo_list = list(bundle.ngos.all())
    scores = [_score_int(n) for n in ngo_list]
    transparency_score = (
        round(sum(scores) / len(scores)) if scores else 0
    )
    return {
        'id': str(bundle.id),
        'name': bundle.name,
        'cause': cause,
        'causeLabel': CAUSE_LABELS.get(cause, cause.replace('-', ' ').title()),
        'description': bundle.description or '',
        'targetAmount': float(bundle.target_amount),
        'raisedAmount': float(bundle.raised_amount),
        'matchMultiplier': bundle.match_multiplier,
        'matchSponsor': bundle.match_sponsor,
        'transparencyScore': transparency_score,
        'isActive': bundle.is_active,
        'ongs': [
            {'id': str(n.id), 'name': n.name, 'score': _score_int(n)}
            for n in ngo_list
        ],
    }


def serialize_bundle_detail(bundle: Bundle) -> dict:
    base = serialize_bundle_list_item(bundle)
    ngo_list = list(bundle.ngos.all())
    base.update({
        'eligibilityRules': bundle.eligibility_rules or [],
        'distributionRules': bundle.distribution_rules or '',
        'ongs': [
            {
                'id': str(n.id),
                'name': n.name,
                'score': _score_int(n),
                'location': _location(n),
            }
            for n in ngo_list
        ],
    })
    return base
