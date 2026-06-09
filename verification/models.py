import uuid
from django.db import models
from django.conf import settings


class NGO(models.Model):
    class VerificationStatus(models.TextChoices):
        VERIFIED = 'verified', 'Verified'
        ANALYSIS = 'analysis', 'In Analysis'
        PENDING = 'pending', 'Pending'
        INCONSISTENT = 'inconsistent', 'Inconsistent'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Primary key (UUID) for the NGO",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ngo_profile',
        null=True,
        blank=True,
        help_text="User account associated with this NGO",
    )
    pix_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Chave PIX da ONG",
    )
    external_api_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="External API ID if integrated",
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the NGO",
    )
    cnpj = models.CharField(
        max_length=18,
        unique=True,
        help_text="CNPJ of the NGO (formatted or unformatted)",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the NGO",
    )
    focus_area = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Focus area of the NGO",
    )
    city = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="City where the NGO is registered",
    )
    state = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text="State abbreviation (UF)",
    )
    current_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        blank=True,
        null=True,
        help_text="Current evaluation score (0-100)",
    )
    last_external_audit = models.DateField(
        blank=True,
        null=True,
        help_text="Date of the last external audit",
    )
    years_operating = models.PositiveIntegerField(
        default=0,
        help_text="Years of operation based on CNPJ opening date",
    )
    address_valid = models.BooleanField(
        default=False,
        help_text="Whether the registered address matches public CEP data",
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        help_text="Current verification status of the NGO",
    )
    last_verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of the last automated verification",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Flag indicating if the NGO CNPJ is active",
    )
    social_networks = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of social network entries, e.g. "
            '[{"platform": "instagram", "handle": "@ong"}]'
        ),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        db_table = 'ngo'
        verbose_name = "NGO"
        verbose_name_plural = "NGOs"

    def __str__(self):
        return self.name


class Campaign(models.Model):
    """An individual fundraising campaign run by a single NGO."""

    class Status(models.TextChoices):
        DRAFT = 'rascunho', 'Rascunho'
        IN_REVIEW = 'em-revisao', 'Em Revisão'
        APPROVED = 'aprovada', 'Aprovada'
        PUBLISHED = 'publicada', 'Publicada'
        REJECTED = 'recusada', 'Recusada'
        ENDED = 'encerrada', 'Encerrada'
        ARCHIVED = 'arquivada', 'Arquivada'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255)
    ngo = models.ForeignKey(
        NGO,
        on_delete=models.CASCADE,
        related_name='campaigns',
        help_text="The NGO running this campaign",
    )
    description = models.TextField(blank=True, null=True)
    cause = models.CharField(
        max_length=50,
        help_text="Cause slug, e.g. 'meio-ambiente'",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    end_date = models.DateField(blank=True, null=True, help_text="Campaign expiration date")
    
    match_multiplier = models.PositiveSmallIntegerField(
        default=1,
        help_text="Matchfunding multiplier (1 = no match)",
    )
    match_sponsor = models.CharField(max_length=255, blank=True, null=True)
    match_cap = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, help_text="Maximum matchfunding amount limit")
    match_period = models.CharField(max_length=100, blank=True, null=True, help_text="E.g., 'Jun-Ago 2026'")
    
    requirements = models.TextField(blank=True, null=True, help_text="Specific requirements for the campaign")
    destination = models.TextField(blank=True, null=True, help_text="How the funds will be used")
    
    location = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'campaign'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Bundle(models.Model):
    """A collective campaign backed by multiple NGOs."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=255)
    cause = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    match_multiplier = models.PositiveSmallIntegerField(default=1)
    match_sponsor = models.CharField(max_length=255, blank=True, null=True)
    ngos = models.ManyToManyField(
        NGO,
        related_name='bundles',
        blank=True,
    )
    eligibility_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="List of eligibility rule strings",
    )
    distribution_rules = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bundle'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
