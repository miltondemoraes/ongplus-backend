from django.db import models
import uuid
from verification.models import NGO

class ChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        APPROVED = 'approved', 'Aprovada'
        REJECTED = 'rejected', 'Rejeitada'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ong = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='change_requests')
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request {self.id} for {self.ong.name} ({self.status})"

def ngo_document_upload_path(instance, filename):
    return f'ngo_documents/{instance.ong_id}/{filename}'


class NGODocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ong = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    document_url = models.URLField(blank=True, null=True)
    file = models.FileField(upload_to=ngo_document_upload_path, blank=True, null=True)
    is_public = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.ong.name}"


class NGOReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ong = models.ForeignKey(NGO, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=255)
    period = models.CharField(max_length=50, help_text="e.g. '30-days', '3-months', 'custom'")
    include_finance = models.BooleanField(default=True)
    include_donors = models.BooleanField(default=True)
    include_campaigns = models.BooleanField(default=False)
    include_cnpj = models.BooleanField(default=True)
    pdf_file = models.FileField(upload_to='ngo_reports/%Y/%m/', blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']

    def delete(self, *args, **kwargs):
        if self.pdf_file:
            self.pdf_file.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.ong.name}"
