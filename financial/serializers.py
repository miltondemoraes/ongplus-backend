from rest_framework import serializers
from decimal import Decimal
from .models import Campaign, PaymentMethod, Donation, PaymentTransaction, FinancialRecord
from verification.models import NGO
from authentication.models import CustomUser


class CampaignSerializer(serializers.ModelSerializer):
    ong_name = serializers.CharField(source='ong.name', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    is_active_campaign = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            'id', 'ong', 'ong_name', 'title', 'description',
            'target_amount', 'current_amount', 'status',
            'start_date', 'end_date', 'image_url',
            'progress_percentage', 'is_active_campaign', 'days_remaining',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'current_amount', 'created_at', 'updated_at']

    def get_progress_percentage(self, obj):
        return round(obj.progress_percentage, 2)

    def get_is_active_campaign(self, obj):
        return obj.is_active_campaign

    def get_days_remaining(self, obj):
        from django.utils import timezone
        delta = obj.end_date - timezone.now()
        return max(delta.days, 0)

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError(
                "Data de início deve ser anterior à data de término."
            )
        if data['target_amount'] <= 0:
            raise serializers.ValidationError(
                "Valor alvo deve ser maior que zero."
            )
        return data


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'method_type', 'name', 'is_active', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    donation_amount = serializers.DecimalField(
        source='donation.amount', read_only=True, max_digits=12, decimal_places=2
    )

    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'donation', 'external_id', 'status',
            'amount', 'fee', 'net_amount', 'donation_amount',
            'error_message', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'external_id',
            'fee', 'net_amount'
        ]


class DonationSerializer(serializers.ModelSerializer):
    donor_name = serializers.CharField(source='donor.full_name', read_only=True)
    ong_name = serializers.CharField(source='ong.name', read_only=True)
    campaign_title = serializers.CharField(source='campaign.title', read_only=True)
    transaction = PaymentTransactionSerializer(read_only=True)
    payment_method_name = serializers.CharField(
        source='payment_method.name', read_only=True
    )

    class Meta:
        model = Donation
        fields = [
            'id', 'donor', 'donor_name', 'campaign', 'campaign_title',
            'ong', 'ong_name', 'amount', 'payment_method', 'payment_method_name',
            'status', 'recurrence_type', 'is_anonymous', 'notes',
            'transaction', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'donor', 'status', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Valor da doação deve ser maior que zero.")
        return value

    def validate(self, data):
        if data.get('campaign') and data['campaign'].ong != data['ong']:
            raise serializers.ValidationError(
                "A campanha deve pertencer à mesma ONG da doação."
            )
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['donor'] = request.user
        return super().create(validated_data)


class DonationDetailSerializer(DonationSerializer):
    donor_email = serializers.CharField(source='donor.email', read_only=True)
    campaign_status = serializers.CharField(
        source='campaign.status', read_only=True
    )
    payment_method_type = serializers.CharField(
        source='payment_method.get_method_type_display', read_only=True
    )

    class Meta(DonationSerializer.Meta):
        fields = DonationSerializer.Meta.fields + [
            'donor_email', 'campaign_status', 'payment_method_type'
        ]


class FinancialRecordSerializer(serializers.ModelSerializer):
    ong_name = serializers.CharField(source='ong.name', read_only=True)

    class Meta:
        model = FinancialRecord
        fields = [
            'id', 'ong', 'ong_name', 'record_type', 'amount',
            'description', 'reference_id', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CampaignStatsSerializer(serializers.Serializer):
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    total_raised = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_target = serializers.DecimalField(max_digits=12, decimal_places=2)
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)


class DonationStatsSerializer(serializers.Serializer):
    total_donations = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_donation = serializers.DecimalField(max_digits=12, decimal_places=2)
    completed_donations = serializers.IntegerField()
    failed_donations = serializers.IntegerField()
