import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from authentication.models import CustomUser
from verification.models import NGO


class Campaign(models.Model):
    """Campanha de arrecadação de fundos"""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Rascunho'
        ACTIVE = 'active', 'Ativa'
        PAUSED = 'paused', 'Pausada'
        COMPLETED = 'completed', 'Concluída'
        CANCELLED = 'cancelled', 'Cancelada'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ong = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='fundraising_campaigns')
    title = models.CharField(max_length=255)
    description = models.TextField()
    target_amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    current_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    image_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ong', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.title} - {self.ong.name}"

    @property
    def progress_percentage(self):
        if self.target_amount == 0:
            return 0
        return min((self.current_amount / self.target_amount) * 100, 100)

    @property
    def is_active_campaign(self):
        now = timezone.now()
        return (
            self.status == self.Status.ACTIVE
            and self.start_date <= now <= self.end_date
        )


class PaymentMethod(models.Model):
    """Métodos de pagamento disponíveis"""
    class MethodType(models.TextChoices):
        CREDIT_CARD = 'credit_card', 'Cartão de Crédito'
        DEBIT_CARD = 'debit_card', 'Cartão de Débito'
        PIX = 'pix', 'PIX'
        BANK_TRANSFER = 'bank_transfer', 'Transferência Bancária'
        DIGITAL_WALLET = 'digital_wallet', 'Carteira Digital'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    method_type = models.CharField(max_length=20, choices=MethodType.choices)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['method_type', 'name']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_method_type_display()})"


class Donation(models.Model):
    """Modelo de doação"""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        PROCESSING = 'processing', 'Processando'
        COMPLETED = 'completed', 'Concluída'
        FAILED = 'failed', 'Falha'
        REFUNDED = 'refunded', 'Reembolsada'

    class RecurrenceType(models.TextChoices):
        ONCE = 'once', 'Uma vez'
        MONTHLY = 'monthly', 'Mensal'
        QUARTERLY = 'quarterly', 'Trimestral'
        ANNUAL = 'annual', 'Anual'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donor = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, related_name='donations'
    )
    campaign = models.ForeignKey(
        Campaign, on_delete=models.SET_NULL, null=True, related_name='donations'
    )
    ong = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='donations')
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, related_name='donations'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    recurrence_type = models.CharField(
        max_length=20, choices=RecurrenceType.choices, default=RecurrenceType.ONCE
    )
    is_anonymous = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['donor', 'status']),
            models.Index(fields=['ong', 'status']),
            models.Index(fields=['campaign', 'status']),
        ]

    def __str__(self):
        donor_info = 'Anônimo' if self.is_anonymous else self.donor.email
        return f"Doação de {donor_info} - R$ {self.amount}"


class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        INITIATED = 'initiated', 'Iniciada'
        PROCESSING = 'processing', 'Processando'
        AUTHORIZED = 'authorized', 'Autorizada'
        CAPTURED = 'captured', 'Capturada'
        DECLINED = 'declined', 'Recusada'
        EXPIRED = 'expired', 'Expirada'
        CANCELLED = 'cancelled', 'Cancelada'
        REFUNDED = 'refunded', 'Reembolsada'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.OneToOneField(
        Donation, on_delete=models.CASCADE, related_name='transaction'
    )
    external_id = models.CharField(
        max_length=255, unique=True, null=True, blank=True,
        help_text='ID da transação no gateway de pagamento'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['donation', 'status']),
            models.Index(fields=['external_id']),
        ]

    def __str__(self):
        return f"Transação {self.id} - {self.get_status_display()}"


class FinancialRecord(models.Model):
    """Registro de histórico financeiro (simplificado)"""
    class RecordType(models.TextChoices):
        DONATION = 'donation', 'Doação'
        FEE = 'fee', 'Taxa'
        REFUND = 'refund', 'Reembolso'
        TRANSFER = 'transfer', 'Transferência'
        ADJUSTMENT = 'adjustment', 'Ajuste'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ong = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='financial_records')
    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    reference_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ong', 'created_at']),
            models.Index(fields=['record_type']),
        ]

    def __str__(self):
        return f"{self.get_record_type_display()} - R$ {self.amount} - {self.ong.name}"