from django.db.models import Count, Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from financial.models import Donation

from .models import CustomUser, DonorProfile


CAUSE_LABELS = {
    'meio-ambiente': 'Meio Ambiente',
    'educacao': 'Educação',
    'saude': 'Saúde',
    'direitos-humanos': 'Direitos Humanos',
    'clima': 'Clima',
}


def _require_donor(request):
    if request.user.role != CustomUser.Role.DONOR:
        return Response(
            {'detail': 'Endpoint disponível apenas para doadores.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _profile_for(user):
    profile, _ = DonorProfile.objects.get_or_create(user=user)
    return profile


def _serialize_cause(value):
    if isinstance(value, dict):
        cause_id = value.get('id') or value.get('slug') or value.get('name')
        label = value.get('label') or value.get('name') or CAUSE_LABELS.get(cause_id, cause_id)
        active = value.get('active', True)
    else:
        cause_id = str(value)
        label = CAUSE_LABELS.get(cause_id, cause_id.replace('-', ' ').title())
        active = True
    return {'id': cause_id, 'label': label, 'active': bool(active)}


def _serialize_donation(donation):
    campaign = donation.campaign
    return {
        'id': str(donation.id),
        'date': donation.created_at.isoformat(),
        'amount': float(donation.amount),
        'status': donation.status,
        'recurrenceType': donation.recurrence_type,
        'ngo': {
            'id': str(donation.ong_id),
            'name': donation.ong.name,
        },
        'campaign': (
            {
                'id': str(campaign.id),
                'name': campaign.title,
            }
            if campaign
            else None
        ),
        'receiptUrl': None,
    }


class DonorProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forbidden = _require_donor(request)
        if forbidden:
            return forbidden

        profile = _profile_for(request.user)
        completed = Donation.objects.filter(
            donor=request.user,
            status=Donation.Status.COMPLETED,
        )
        totals = completed.aggregate(
            total_donated=Sum('amount'),
            ngo_count=Count('ong', distinct=True),
            donation_count=Count('id'),
        )
        total_donated = totals['total_donated'] or 0
        ngo_count = totals['ngo_count'] or 0
        donation_count = totals['donation_count'] or 0

        payload = {
            'profile': {
                'id': request.user.id,
                'name': request.user.full_name,
                'email': request.user.email,
                'joinedAt': request.user.date_joined.isoformat(),
                'bio': '',
                'phone': profile.phone,
                'birthDate': profile.birth_date.isoformat() if profile.birth_date else None,
                'impactMetrics': {
                    'hectaresHelped': 0,
                    'personsHelped': 0,
                    'ngoCount': ngo_count,
                    'donationCount': donation_count,
                    'totalDonated': float(total_donated),
                },
            },
            'causePreferences': [
                _serialize_cause(cause)
                for cause in (profile.preferred_causes or [])
            ],
            'donations': [_serialize_donation(donation) for donation in completed],
        }
        return Response(payload)


class DonorDonationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forbidden = _require_donor(request)
        if forbidden:
            return forbidden

        donations = Donation.objects.filter(donor=request.user).select_related('ong', 'campaign')
        return Response([_serialize_donation(donation) for donation in donations])


class DonorCausePreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        forbidden = _require_donor(request)
        if forbidden:
            return forbidden

        profile = _profile_for(request.user)
        return Response([_serialize_cause(cause) for cause in (profile.preferred_causes or [])])

    def patch(self, request):
        forbidden = _require_donor(request)
        if forbidden:
            return forbidden

        raw_preferences = request.data.get('causePreferences', request.data.get('causes', request.data))
        if not isinstance(raw_preferences, list):
            return Response(
                {'detail': 'Envie uma lista de preferências.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        preferences = [_serialize_cause(cause) for cause in raw_preferences]
        profile = _profile_for(request.user)
        profile.preferred_causes = preferences
        profile.save(update_fields=['preferred_causes', 'updated_at'])
        return Response(preferences)
