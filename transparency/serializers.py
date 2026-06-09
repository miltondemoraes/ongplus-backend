from rest_framework import serializers
from .models import ChangeRequest

class ChangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeRequest
        fields = ['id', 'ong', 'field_name', 'old_value', 'new_value', 'reason', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

class GlobalMetricsSerializer(serializers.Serializer):
    week = serializers.DictField()
    month = serializers.DictField()

class TransferSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    ong = serializers.CharField()
    cnpj = serializers.CharField()
    cause = serializers.CharField()
    amount = serializers.FloatField()
    date = serializers.DateTimeField()
    period = serializers.CharField()
    reason = serializers.CharField()
    docType = serializers.CharField()
    docLabel = serializers.CharField()
    criteria = serializers.DictField()
