from django.contrib import admin
from .models import Campaign, PaymentMethod, Donation, PaymentTransaction, FinancialRecord


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'ong', 'status', 'target_amount', 'current_amount', 'progress_percentage', 'created_at']
    list_filter = ['status', 'ong', 'created_at']
    search_fields = ['title', 'description', 'ong__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'progress_percentage']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('id', 'ong', 'title', 'description', 'image_url')
        }),
        ('Metas', {
            'fields': ('target_amount', 'current_amount', 'progress_percentage')
        }),
        ('Período', {
            'fields': ('start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'created_at'


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'method_type', 'is_active', 'created_at']
    list_filter = ['is_active', 'method_type', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Informações', {
            'fields': ('id', 'method_type', 'name', 'description', 'is_active', 'created_at')
        }),
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['id', 'donor_info', 'ong', 'amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'recurrence_type', 'is_anonymous', 'payment_method', 'ong', 'created_at']
    search_fields = ['donor__full_name', 'donor__email', 'ong__name', 'notes']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = (
        ('Doador', {
            'fields': ('id', 'donor', 'is_anonymous')
        }),
        ('Destinatário', {
            'fields': ('ong', 'campaign')
        }),
        ('Valor e Método', {
            'fields': ('amount', 'payment_method')
        }),
        ('Recorrência', {
            'fields': ('recurrence_type',)
        }),
        ('Status e Observações', {
            'fields': ('status', 'notes')
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'created_at'

    def donor_info(self, obj):
        return 'Anônimo' if obj.is_anonymous else obj.donor.email if obj.donor else 'N/A'
    donor_info.short_description = 'Doador'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'donation_amount', 'status', 'amount', 'fee', 'net_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['donation__id', 'external_id', 'error_message']
    readonly_fields = ['id', 'created_at', 'updated_at', 'donation']
    fieldsets = (
        ('Identificação', {
            'fields': ('id', 'donation', 'external_id')
        }),
        ('Valores', {
            'fields': ('amount', 'fee', 'net_amount')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Metadados', {
            'fields': ('metadata',)
        }),
        ('Datas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    date_hierarchy = 'created_at'

    def donation_amount(self, obj):
        return f"R$ {obj.amount:.2f}"
    donation_amount.short_description = 'Valor'


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'ong', 'record_type', 'amount', 'created_at']
    list_filter = ['record_type', 'ong', 'created_at']
    search_fields = ['ong__name', 'description', 'reference_id']
    readonly_fields = ['id', 'created_at']
    fieldsets = (
        ('Informações', {
            'fields': ('id', 'ong', 'record_type')
        }),
        ('Valores', {
            'fields': ('amount',)
        }),
        ('Detalhes', {
            'fields': ('description', 'reference_id')
        }),
        ('Data', {
            'fields': ('created_at',)
        }),
    )
    date_hierarchy = 'created_at'
