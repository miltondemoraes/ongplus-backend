import json
import os
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.db.models import Sum

from .auth_helpers import require_ngo_access
from .models import ChangeRequest, NGODocument, NGOReport
from .report_pdf import build_report_pdf
from .serializers import ChangeRequestSerializer
from verification.models import NGO, Campaign
from financial.models import FinancialRecord, Donation

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_EXTENSIONS = {'.pdf'}


CAUSE_LABELS = {
    'meio-ambiente': 'Meio Ambiente',
    'saude': 'Saúde',
    'educacao': 'Educação',
    'direitos-humanos': 'Direitos Humanos',
}


@require_GET
def global_metrics_view(request):
    now = timezone.now()
    week_ago = now - timezone.timedelta(days=7)
    month_ago = now - timezone.timedelta(days=30)

    week_transfers = FinancialRecord.objects.filter(
        record_type=FinancialRecord.RecordType.TRANSFER,
        created_at__gte=week_ago,
    )
    month_transfers = FinancialRecord.objects.filter(
        record_type=FinancialRecord.RecordType.TRANSFER,
        created_at__gte=month_ago,
    )

    week_raised_agg = Campaign.objects.filter(
        updated_at__gte=week_ago,
        is_active=True,
    ).aggregate(total=Sum('raised_amount'))
    month_raised_agg = Campaign.objects.filter(
        is_active=True,
    ).aggregate(total=Sum('raised_amount'))

    week_raised = float(week_raised_agg['total'] or 0)
    month_raised = float(month_raised_agg['total'] or 0)

    week_distributed = float(week_transfers.aggregate(total=Sum('amount'))['total'] or 0)
    month_distributed = float(month_transfers.aggregate(total=Sum('amount'))['total'] or 0)

    week_ongs = week_transfers.values('ong').distinct().count()
    month_ongs = month_transfers.values('ong').distinct().count()

    def compat(distributed, raised):
        if raised <= 0:
            return 0
        return min(round((distributed / raised) * 100), 100)

    return JsonResponse({
        "week": {
            "raised": week_raised,
            "distributed": week_distributed,
            "ongsCount": week_ongs,
            "compatibility": compat(week_distributed, week_raised),
        },
        "month": {
            "raised": month_raised,
            "distributed": month_distributed,
            "ongsCount": month_ongs,
            "compatibility": compat(month_distributed, month_raised),
        }
    })


@require_GET
def recent_transfers_view(request):
    now = timezone.now()
    month_ago = now - timezone.timedelta(days=30)

    records = (
        FinancialRecord.objects
        .filter(record_type=FinancialRecord.RecordType.TRANSFER, created_at__gte=month_ago)
        .select_related('ong')
        .order_by('-created_at')[:50]
    )

    result = []
    for rec in records:
        ngo = rec.ong
        days_old = (now - rec.created_at).days
        period = 'week' if days_old <= 7 else 'month'
        score = int(ngo.current_score or 0)

        raw_cnpj = ngo.cnpj.replace('.', '').replace('/', '').replace('-', '')
        if len(raw_cnpj) == 14:
            cnpj_display = f"{raw_cnpj[:2]}.{raw_cnpj[2:5]}.{raw_cnpj[5:8]}/{raw_cnpj[8:12]}-{raw_cnpj[12:]}"
        else:
            cnpj_display = ngo.cnpj

        focus_area = ngo.focus_area or ''
        cause_label = CAUSE_LABELS.get(focus_area, focus_area.replace('-', ' ').title())

        result.append({
            "id": str(rec.id),
            "ong": ngo.name,
            "cnpj": cnpj_display,
            "cause": cause_label,
            "amount": float(rec.amount),
            "date": rec.created_at.isoformat(),
            "period": period,
            "reason": rec.description,
            "docType": "receipt",
            "docLabel": f"Recibo #{str(rec.id)[:8].upper()}",
            "criteria": {
                "score": score,
                "yearsActive": ngo.years_operating or 0,
                "addressConsistency": ngo.address_valid,
                "cnpjValidated": ngo.verification_status == 'verified',
                "lastAudit": ngo.last_external_audit.strftime('%b/%Y') if ngo.last_external_audit else "N/D",
                "auditStatus": "Sem Ressalvas" if ngo.verification_status == 'verified' else "Em Análise",
                "documentationComplete": ngo.verification_status in ('verified', 'analysis'),
            },
        })

    return JsonResponse(result, safe=False)


@require_GET
def financial_data_view(request, pk):
    ngo = get_object_or_404(NGO, pk=pk)

    total_transfers = FinancialRecord.objects.filter(
        ong=ngo, record_type=FinancialRecord.RecordType.TRANSFER
    ).aggregate(total=Sum('amount'))['total'] or 0
    total_donations = FinancialRecord.objects.filter(
        ong=ngo, record_type=FinancialRecord.RecordType.DONATION
    ).aggregate(total=Sum('amount'))['total'] or 0

    budget_utilization = 0
    if total_donations > 0:
        budget_utilization = min(round((float(total_transfers) / float(total_donations)) * 100), 100)

    last_audit = ngo.last_external_audit.strftime('%b/%Y') if ngo.last_external_audit else "N/D"
    audit_status = "Sem Ressalvas" if ngo.verification_status == 'verified' else "Em Análise"

    return JsonResponse({
        "budgetUtilization": budget_utilization,
        "lastAudit": last_audit,
        "auditStatus": audit_status,
    })


@require_GET
def change_history_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    requests = ChangeRequest.objects.filter(ong=ong, status=ChangeRequest.Status.APPROVED).order_by('-updated_at')
    history = [
        {
            "id": str(req.id),
            "field": req.field_name,
            "oldValue": req.old_value,
            "newValue": req.new_value,
            "date": req.updated_at.isoformat(),
            "reason": req.reason,
            "approvedBy": "Auditoria ONG+"
        }
        for req in requests
    ]
    if not history:
        history.append({
            "id": "initial",
            "field": "Registro Inicial",
            "oldValue": "",
            "newValue": "Dados confirmados",
            "date": ong.created_at.isoformat(),
            "reason": "Cadastro na plataforma",
            "approvedBy": "Sistema"
        })
    return JsonResponse(history, safe=False)


@require_GET
def pending_requests_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    requests = ChangeRequest.objects.filter(ong=ong, status=ChangeRequest.Status.PENDING)
    serializer = ChangeRequestSerializer(requests, many=True)
    return JsonResponse(serializer.data, safe=False)


@csrf_exempt
@require_POST
def submit_change_request_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    try:
        data = json.loads(request.body)
        change_request = ChangeRequest.objects.create(
            ong=ong,
            field_name=data.get('field_name', 'Update'),
            old_value=data.get('old_value', ''),
            new_value=data.get('new_value', ''),
            reason=data.get('reason', '')
        )
        serializer = ChangeRequestSerializer(change_request)
        return JsonResponse(serializer.data, status=201)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@require_POST
def approve_change_request_view(request, pk):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    change_request.status = ChangeRequest.Status.APPROVED
    change_request.save()
    serializer = ChangeRequestSerializer(change_request)
    return JsonResponse(serializer.data)


@csrf_exempt
@require_POST
def reject_change_request_view(request, pk):
    change_request = get_object_or_404(ChangeRequest, pk=pk)
    change_request.status = ChangeRequest.Status.REJECTED
    change_request.save()
    serializer = ChangeRequestSerializer(change_request)
    return JsonResponse(serializer.data)

def _document_url(request, doc):
    if doc.file:
        return request.build_absolute_uri(doc.file.url)
    return doc.document_url or ''


def _serialize_document(request, doc):
    return {
        'id': str(doc.id),
        'title': doc.title,
        'description': doc.description or '',
        'documentUrl': _document_url(request, doc),
        'uploadedAt': doc.uploaded_at.isoformat(),
        'isPublic': doc.is_public,
    }


@require_GET
def ngo_documents_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    documents = NGODocument.objects.filter(ong=ong, is_public=True)
    return JsonResponse([_serialize_document(request, doc) for doc in documents], safe=False)


@csrf_exempt
@require_POST
def upload_ngo_document_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    _, error_response = require_ngo_access(request, ong)
    if error_response:
        return error_response

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'Arquivo PDF é obrigatório.'}, status=400)

    extension = os.path.splitext(uploaded_file.name)[1].lower()
    if extension not in ALLOWED_DOCUMENT_EXTENSIONS:
        return JsonResponse({'error': 'Apenas arquivos PDF são permitidos.'}, status=400)

    if uploaded_file.size > MAX_DOCUMENT_SIZE_BYTES:
        return JsonResponse({'error': 'O arquivo deve ter no máximo 10 MB.'}, status=400)

    title = (request.POST.get('title') or uploaded_file.name).strip()[:255]
    description = (request.POST.get('description') or 'Documento comprobatório enviado via painel de gestão.').strip()

    document = NGODocument.objects.create(
        ong=ong,
        title=title,
        description=description,
        file=uploaded_file,
        is_public=False,
    )

    return JsonResponse(_serialize_document(request, document), status=201)


PERIOD_LABELS = {
    '30-days': 'Últimos 30 dias',
    '3-months': 'Últimos 3 meses',
    'custom': 'Período personalizado',
}


def _serialize_change_request(req):
    return {
        'id': str(req.id),
        'field_name': req.field_name,
        'old_value': req.old_value,
        'new_value': req.new_value,
        'reason': req.reason,
        'status': req.status,
        'created_at': req.created_at.isoformat(),
        'updated_at': req.updated_at.isoformat(),
    }


def _serialize_report(report):
    return {
        'id': str(report.id),
        'title': report.title,
        'period': report.period,
        'periodLabel': PERIOD_LABELS.get(report.period, report.period),
        'includeFinance': report.include_finance,
        'includeDonors': report.include_donors,
        'includeCampaigns': report.include_campaigns,
        'includeCnpj': report.include_cnpj,
        'generatedAt': report.generated_at.isoformat(),
        'hasPdf': bool(report.pdf_file),
    }


def _cleanup_orphan_report_files():
    reports_dir = Path(settings.MEDIA_ROOT) / 'ngo_reports'
    if not reports_dir.is_dir():
        return 0

    referenced = {
        report.pdf_file.name
        for report in NGOReport.objects.exclude(pdf_file='')
        if report.pdf_file
    }

    removed = 0
    for file_path in reports_dir.rglob('*.pdf'):
        relative_path = file_path.relative_to(settings.MEDIA_ROOT).as_posix()
        if relative_path not in referenced:
            file_path.unlink(missing_ok=True)
            removed += 1
    return removed


def _build_report_summary(ong, period, options):
    now = timezone.now()
    days = 30 if period == '30-days' else 90 if period == '3-months' else 30
    since = now - timezone.timedelta(days=days)

    ong_data = {'id': str(ong.id), 'name': ong.name}
    if options.get('include_cnpj', True):
        ong_data['cnpj'] = ong.cnpj

    summary = {
        'ong': ong_data,
        'period': PERIOD_LABELS.get(period, period),
        'generatedAt': now.isoformat(),
        'score': int(float(ong.current_score or 0)),
    }

    if options.get('include_finance', True):
        records = FinancialRecord.objects.filter(ong=ong, created_at__gte=since)
        donations = records.filter(record_type=FinancialRecord.RecordType.DONATION)
        transfers = records.filter(record_type=FinancialRecord.RecordType.TRANSFER)
        summary['finance'] = {
            'totalIncome': float(donations.aggregate(total=Sum('amount'))['total'] or 0),
            'totalDistributed': float(transfers.aggregate(total=Sum('amount'))['total'] or 0),
        }

    if options.get('include_donors', True):
        donations_qs = Donation.objects.filter(
            ong=ong,
            status=Donation.Status.COMPLETED,
            created_at__gte=since,
        )
        summary['donors'] = {
            'donationCount': donations_qs.count(),
            'uniqueDonors': donations_qs.values('donor').distinct().count(),
            'totalAmount': float(donations_qs.aggregate(total=Sum('amount'))['total'] or 0),
        }

    if options.get('include_campaigns', False):
        campaigns = Campaign.objects.filter(ngo=ong, is_active=True)
        summary['campaigns'] = {
            'activeCount': campaigns.filter(status=Campaign.Status.PUBLISHED).count(),
            'totalRaised': float(campaigns.aggregate(total=Sum('raised_amount'))['total'] or 0),
        }

    if options.get('include_cnpj', True):
        summary['cnpj'] = ong.cnpj

    return summary


@require_GET
def change_requests_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    requests = ChangeRequest.objects.filter(ong=ong).order_by('-created_at')
    return JsonResponse([_serialize_change_request(req) for req in requests], safe=False)


@csrf_exempt
@require_http_methods(['GET', 'DELETE'])
def ngo_reports_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    _, error = require_ngo_access(request, ong)
    if error:
        return error

    if request.method == 'DELETE':
        reports = list(NGOReport.objects.filter(ong=ong))
        deleted_count = len(reports)
        for report in reports:
            report.delete()
        orphans_removed = _cleanup_orphan_report_files()
        return JsonResponse({
            'deleted': deleted_count,
            'orphansRemoved': orphans_removed,
        })

    reports = NGOReport.objects.filter(ong=ong).order_by('-generated_at')[:20]
    return JsonResponse([_serialize_report(report) for report in reports], safe=False)


@csrf_exempt
@require_POST
def generate_report_view(request, pk):
    ong = get_object_or_404(NGO, pk=pk)
    _, error = require_ngo_access(request, ong)
    if error:
        return error
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido.'}, status=400)

    period = data.get('period', '30-days')
    options = {
        'include_finance': data.get('include_finance', True),
        'include_donors': data.get('include_donors', True),
        'include_campaigns': data.get('include_campaigns', False),
        'include_cnpj': data.get('include_cnpj', True),
    }
    period_label = PERIOD_LABELS.get(period, period)
    title = data.get('title') or f'Relatório de Impacto — {period_label}'

    report = NGOReport.objects.create(
        ong=ong,
        title=title,
        period=period,
        include_finance=options['include_finance'],
        include_donors=options['include_donors'],
        include_campaigns=options['include_campaigns'],
        include_cnpj=options['include_cnpj'],
    )
    try:
        summary = _build_report_summary(ong, period, options)
        pdf_bytes = build_report_pdf(summary, title)
        filename = f'relatorio-{str(report.id)[:8]}.pdf'
        report.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    except Exception:
        report.delete()
        return JsonResponse({'error': 'Falha ao gerar o PDF do relatório.'}, status=500)

    return JsonResponse({
        'report': _serialize_report(report),
    }, status=201)


@require_GET
def download_report_view(request, pk, report_id):
    ong = get_object_or_404(NGO, pk=pk)
    _, error = require_ngo_access(request, ong)
    if error:
        return error
    report = get_object_or_404(NGOReport, pk=report_id, ong=ong)
    if not report.pdf_file:
        return JsonResponse({'error': 'Arquivo PDF não disponível para este relatório.'}, status=404)

    filename = report.pdf_file.name.split('/')[-1]
    response = FileResponse(report.pdf_file.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
