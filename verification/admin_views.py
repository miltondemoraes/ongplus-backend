import json

from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from transparency.models import NGODocument
from transparency.views import _serialize_document
from .admin_auth import require_admin
from .models import NGO, Campaign, Bundle
from .ngo_response import (
    serialize_ngo_detail,
    serialize_ngo_list_item,
    serialize_campaign,
    serialize_bundle_detail,
    serialize_bundle_list_item,
    build_verification_payload,
    get_allocation_criteria,
)
from .services.validation_service import validate_ngo
from .services.cnpj_service import ExternalApiError


REVIEW_NGO_STATUSES = (
    NGO.VerificationStatus.ANALYSIS,
    NGO.VerificationStatus.PENDING,
    NGO.VerificationStatus.INCONSISTENT,
)


@require_GET
def admin_review_ngos_view(request):
    _, error = require_admin(request)
    if error:
        return error
    ngos = NGO.objects.filter(verification_status__in=REVIEW_NGO_STATUSES).order_by('-updated_at')
    return JsonResponse([serialize_ngo_list_item(ngo) for ngo in ngos], safe=False)


@require_GET
def admin_review_campaigns_view(request):
    _, error = require_admin(request)
    if error:
        return error
    campaigns = (
        Campaign.objects.filter(status=Campaign.Status.IN_REVIEW, is_active=True)
        .select_related('ngo')
        .order_by('-created_at')
    )
    return JsonResponse([serialize_campaign(c) for c in campaigns], safe=False)


@require_GET
def admin_list_ngos_view(request):
    _, error = require_admin(request)
    if error:
        return error
    ngos = NGO.objects.all().order_by('-current_score', 'name')
    return JsonResponse([serialize_ngo_detail(ngo) for ngo in ngos], safe=False)


@require_GET
def admin_ngo_documents_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    ngo = get_object_or_404(NGO, pk=pk)
    documents = NGODocument.objects.filter(ong=ngo).order_by('-uploaded_at')
    return JsonResponse([_serialize_document(request, doc) for doc in documents], safe=False)


@csrf_exempt
@require_http_methods(['PATCH'])
def admin_ngo_verification_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    ngo = get_object_or_404(NGO, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    status = data.get('status')
    valid_statuses = {s.value for s in NGO.VerificationStatus}
    if status not in valid_statuses:
        return JsonResponse({'error': f'Status inválido. Use: {", ".join(sorted(valid_statuses))}'}, status=400)

    ngo.verification_status = status
    if status == NGO.VerificationStatus.VERIFIED:
        ngo.last_verified_at = timezone.now()
    ngo.save()
    return JsonResponse(serialize_ngo_detail(ngo))


@csrf_exempt
@require_http_methods(['PATCH'])
def admin_ngo_score_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    ngo = get_object_or_404(NGO, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    score = data.get('score')
    if score is None:
        return JsonResponse({'error': 'Campo score é obrigatório.'}, status=400)
    try:
        score = float(score)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Score deve ser numérico.'}, status=400)
    if score < 0 or score > 100:
        return JsonResponse({'error': 'Score deve estar entre 0 e 100.'}, status=400)

    ngo.current_score = score
    ngo.save(update_fields=['current_score', 'updated_at'])
    return JsonResponse(serialize_ngo_detail(ngo))


@csrf_exempt
@require_POST
def admin_ngo_validate_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    ngo = get_object_or_404(NGO, pk=pk)
    try:
        result = validate_ngo(ngo.cnpj, persist=False)
        ngo.refresh_from_db()
        return JsonResponse({
            'validation': result,
            'ngo': serialize_ngo_detail(ngo),
            'verification': build_verification_payload(ngo),
        })
    except ExternalApiError as e:
        return JsonResponse({'error': str(e)}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['DELETE'])
def admin_ngo_delete_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    ngo = get_object_or_404(NGO, pk=pk)
    ngo_name = ngo.name
    user = ngo.user
    ngo.delete()
    if user:
        user.delete()
    return JsonResponse({'deleted': True, 'name': ngo_name})


@require_GET
def admin_list_campaigns_view(request):
    _, error = require_admin(request)
    if error:
        return error
    campaigns = Campaign.objects.filter(is_active=True).select_related('ngo').order_by('-created_at')
    return JsonResponse([serialize_campaign(c) for c in campaigns], safe=False)


@csrf_exempt
@require_http_methods(['PATCH'])
def admin_campaign_review_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    campaign = get_object_or_404(Campaign, pk=pk, is_active=True)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    status = data.get('status')
    allowed = {
        Campaign.Status.APPROVED,
        Campaign.Status.PUBLISHED,
        Campaign.Status.REJECTED,
        Campaign.Status.IN_REVIEW,
    }
    if status not in allowed:
        return JsonResponse({'error': 'Status inválido para revisão.'}, status=400)

    campaign.status = status
    campaign.save()
    return JsonResponse(serialize_campaign(campaign))


@csrf_exempt
@require_http_methods(['PATCH'])
def admin_campaign_end_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    campaign = get_object_or_404(Campaign, pk=pk, is_active=True)
    campaign.status = Campaign.Status.ENDED
    campaign.save()
    return JsonResponse(serialize_campaign(campaign))


@require_GET
def admin_score_criteria_view(request):
    _, error = require_admin(request)
    if error:
        return error
    return JsonResponse(get_allocation_criteria(), safe=False)


@require_GET
def admin_list_bundles_view(request):
    _, error = require_admin(request)
    if error:
        return error
    bundles = Bundle.objects.prefetch_related('ngos').order_by('-created_at')
    return JsonResponse([serialize_bundle_detail(b) for b in bundles], safe=False)


@csrf_exempt
@require_http_methods(['POST'])
def admin_create_bundle_view(request):
    _, error = require_admin(request)
    if error:
        return error
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    bundle = Bundle.objects.create(
        name=data.get('name', '').strip(),
        cause=data.get('cause', 'outros'),
        description=data.get('description', ''),
        target_amount=data.get('targetAmount', 0),
        match_multiplier=data.get('matchMultiplier', 1),
        match_sponsor=data.get('matchSponsor', ''),
        distribution_rules=data.get('distributionRules', ''),
        eligibility_rules=data.get('eligibilityRules', []),
    )
    ngo_ids = data.get('ngoIds', [])
    if ngo_ids:
        ngos = NGO.objects.filter(id__in=ngo_ids)
        bundle.ngos.set(ngos)
    return JsonResponse(serialize_bundle_detail(bundle), status=201)


@csrf_exempt
@require_http_methods(['PATCH'])
def admin_bundle_update_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    bundle = get_object_or_404(Bundle, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    if 'name' in data:
        bundle.name = data['name']
    if 'cause' in data:
        bundle.cause = data['cause']
    if 'description' in data:
        bundle.description = data['description']
    if 'targetAmount' in data:
        bundle.target_amount = data['targetAmount']
    if 'matchMultiplier' in data:
        bundle.match_multiplier = data['matchMultiplier']
    if 'matchSponsor' in data:
        bundle.match_sponsor = data['matchSponsor']
    if 'distributionRules' in data:
        bundle.distribution_rules = data['distributionRules']
    if 'eligibilityRules' in data:
        bundle.eligibility_rules = data['eligibilityRules']
    bundle.save()
    return JsonResponse(serialize_bundle_detail(bundle))


@csrf_exempt
@require_POST
def admin_bundle_add_ngo_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    bundle = get_object_or_404(Bundle, pk=pk)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    ngo_id = data.get('ngoId')
    if not ngo_id:
        return JsonResponse({'error': 'ngoId é obrigatório.'}, status=400)
    ngo = get_object_or_404(NGO, pk=ngo_id)
    bundle.ngos.add(ngo)
    return JsonResponse(serialize_bundle_detail(bundle))


@csrf_exempt
@require_http_methods(['DELETE'])
def admin_bundle_remove_ngo_view(request, pk, ngo_pk):
    _, error = require_admin(request)
    if error:
        return error
    bundle = get_object_or_404(Bundle, pk=pk)
    ngo = get_object_or_404(NGO, pk=ngo_pk)
    bundle.ngos.remove(ngo)
    return JsonResponse(serialize_bundle_detail(bundle))


@csrf_exempt
@require_http_methods(['PATCH'])
def admin_bundle_end_view(request, pk):
    _, error = require_admin(request)
    if error:
        return error
    bundle = get_object_or_404(Bundle, pk=pk)
    bundle.is_active = False
    bundle.save()
    return JsonResponse(serialize_bundle_list_item(bundle))
