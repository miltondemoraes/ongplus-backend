import json
from datetime import timedelta
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import NGO, Campaign, Bundle
from .ngo_response import (
    serialize_ngo_list_item,
    serialize_ngo_detail,
    build_verification_payload,
    get_allocation_criteria,
    serialize_campaign,
    serialize_bundle_list_item,
    serialize_bundle_detail,
)
from .services.validation_service import validate_ngo
from .services.cnpj_service import ExternalApiError
from .exceptions import CnpjNotFound


@require_GET
def health_check_view(request):
    return JsonResponse({"status": "ok"})


@require_GET
def list_ngos_view(request):
    ngos = NGO.objects.all().order_by('-current_score', 'name')
    return JsonResponse([serialize_ngo_list_item(ngo) for ngo in ngos], safe=False)


@require_GET
def ngo_detail_view(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)
    return JsonResponse(serialize_ngo_detail(ngo))


@require_GET
def ngo_verification_view(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)
    payload = build_verification_payload(ngo)
    payload['score'] = payload['criteria']['score']
    return JsonResponse(payload)


@require_GET
def allocation_criteria_view(request):
    return JsonResponse(get_allocation_criteria(), safe=False)


@csrf_exempt
@require_POST
def validate_ong_view(request):
    """
    Endpoint POST /api/ong-validation/
    Receives CNPJ, validates input, calls the verification orchestrator,
    and returns computed score, status, and validation flags.
    """
    try:
        body = json.loads(request.body)
        cnpj_input = body.get('cnpj', '')
        if isinstance(cnpj_input, str):
            cnpj_input = cnpj_input.strip()
            
        if not cnpj_input:
            return JsonResponse({"cnpj": "CNPJ is required.", "error": "CNPJ is required."}, status=400)
        
        cnpj_digits = ''.join(filter(str.isdigit, str(cnpj_input)))
        if len(cnpj_digits) != 14:
            return JsonResponse({"error": "CNPJ format is invalid."}, status=400)
        
        result = validate_ngo(cnpj_input)
        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    except ValueError as e:
        return JsonResponse({"error": str(e), "cnpj": str(e)}, status=400)
    except CnpjNotFound as e:
        return JsonResponse({"error": str(e)}, status=404)
    except ExternalApiError as e:
        return JsonResponse({"error": str(e)}, status=502)
    except Exception as e:
        return JsonResponse(
            {"error": f"An unexpected error occurred: {str(e)}"},
            status=500,
        )


@require_GET
def list_campaigns_view(request):
    campaigns = Campaign.objects.filter(is_active=True, status=Campaign.Status.PUBLISHED).select_related('ngo').order_by('-created_at')
    return JsonResponse([serialize_campaign(c) for c in campaigns], safe=False)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def ngo_campaigns_view(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)
    
    if request.method == "GET":
        campaigns = Campaign.objects.filter(ngo=ngo, is_active=True).order_by('-created_at')
        return JsonResponse([serialize_campaign(c) for c in campaigns], safe=False)
        
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            days_left = int(data.get('daysLeft', 30))
            end_date = timezone.now().date() + timedelta(days=days_left)
            
            campaign = Campaign.objects.create(
                ngo=ngo,
                name=data.get('name'),
                description=data.get('description', ''),
                cause=data.get('cause', 'outros'),
                status=data.get('status', Campaign.Status.DRAFT),
                target_amount=data.get('targetAmount', 0),
                end_date=end_date,
                match_multiplier=data.get('matchMultiplier', 1),
                match_sponsor=data.get('matchSponsor', ''),
                match_cap=data.get('matchCap'),
                match_period=data.get('matchPeriod', ''),
                requirements=data.get('requirements', ''),
                destination=data.get('destination', '')
            )
            return JsonResponse(serialize_campaign(campaign), status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
def campaign_detail_view(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk, is_active=True)
    try:
        data = json.loads(request.body)
        campaign.name = data.get('name', campaign.name)
        campaign.description = data.get('description', campaign.description)
        campaign.cause = data.get('cause', campaign.cause)
        
        if 'status' in data:
            campaign.status = data.get('status')
            
        campaign.target_amount = data.get('targetAmount', campaign.target_amount)
        
        if 'daysLeft' in data:
            days_left = int(data.get('daysLeft'))
            campaign.end_date = timezone.now().date() + timedelta(days=days_left)
            
        campaign.match_multiplier = data.get('matchMultiplier', campaign.match_multiplier)
        campaign.match_sponsor = data.get('matchSponsor', campaign.match_sponsor)
        campaign.match_cap = data.get('matchCap', campaign.match_cap)
        campaign.match_period = data.get('matchPeriod', campaign.match_period)
        campaign.requirements = data.get('requirements', campaign.requirements)
        campaign.destination = data.get('destination', campaign.destination)
        
        campaign.save()
        return JsonResponse(serialize_campaign(campaign))
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["PATCH"])
def campaign_status_view(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk, is_active=True)
    try:
        data = json.loads(request.body)
        if 'status' in data:
            campaign.status = data['status']
            campaign.save()
            return JsonResponse(serialize_campaign(campaign))
        return JsonResponse({"error": "Status required"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@require_GET
def list_bundles_view(request):
    bundles = Bundle.objects.filter(is_active=True).prefetch_related('ngos').order_by('-created_at')
    return JsonResponse([serialize_bundle_list_item(b) for b in bundles], safe=False)


@require_GET
def bundle_detail_view(request, pk):
    bundle = get_object_or_404(Bundle, pk=pk, is_active=True)
    return JsonResponse(serialize_bundle_detail(bundle))


@require_GET
def ngo_data_sources_view(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)
    
    # Calculate times relative to the NGO's verification status
    last_verified = ngo.last_verified_at or ngo.updated_at
    hours_ago = int((timezone.now() - last_verified).total_seconds() / 3600)
    
    receita_sync = "Agora" if hours_ago < 1 else f"{hours_ago} horas atrás"
    brasil_api_sync = "1 dia atrás" if hours_ago < 24 else f"{int(hours_ago/24)} dias atrás"

    sources = [
        {"name": "Receita Federal", "lastSync": receita_sync, "status": "success" if ngo.is_active else "warning"},
        {"name": "Brasil API", "lastSync": brasil_api_sync, "status": "success"},
        {"name": "Base Própria", "lastSync": "Agora", "status": "success"},
    ]
    
    return JsonResponse(sources, safe=False)
