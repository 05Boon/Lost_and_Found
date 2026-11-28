from django.db import models
from django.conf import settings

# Create your models here.
class ItemReport(models.Model):
    REPORT_TYPES = [
        ('lost', 'Lost Item'),
        ( 'found', 'Found Item')
    ]

    STATUS_CHOICES = [
        ('active', 'Active',),
        ('under review', 'Under Review',),
        ('matched', 'Matched',),
        ('recovered', 'Recovered',),
        ('closed', 'Closed',),
        ('hidden', 'Hidden',),
    ]

    CATEGORY_CHOICES = [
        ('electronics', 'Electronics',),
        ('clothing', 'Clothing',),
        ('documents', 'Documents',),
        ('accessories', 'Accessories',),
        ('other', 'Other',),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    report_type = models.CharField(
        max_length=10,
        choices=REPORT_TYPES
    )
    title = models.CharField(max_length=150)

    description = models.TextField()

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
    )

    date_lost_or_found = models.DateField()
    location = models.CharField(max_length=200)

    image = models.ImageField(
        upload_to='item_images/',
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Claim(models.Model):
    CLAIM_STATUS = [
        ('pending', 'Pending'),
        ('more_info', 'More Information Required'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    private_evidence = models.TextField()
    claim_status = models.CharField(
        max_length=20,
        choices=CLAIM_STATUS,
        default='pending'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims'
    )
    decision_note = models.TextField(
        blank=True
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True
    )
    decided_at = models.DateTimeField(
        null=True,
        blank=True
    )
    def __str__(self):
        return f"Claim {self.id} - {self.report.title}"

class Handover(models.Model):

    report = models.ForeignKey(
        ItemReport,
        on_delete=models.CASCADE,
        related_name='handovers'
    )

    claim = models.ForeignKey(
        Claim,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    handover_date = models.DateTimeField()

    outcome = models.CharField(
        max_length=100
    )

    notes = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"Handover for {self.report.title}"

class StatusHistory(models.Model):

    ENTITY_TYPES = [
        ('report', 'Report'),
        ('claim', 'Claim'),
    ]

    entity_type = models.CharField(
        max_length=10,
        choices=ENTITY_TYPES
    )

    entity_id = models.PositiveIntegerField()

    previous_status = models.CharField(
        max_length=30,
        blank=True
    )

    new_status = models.CharField(
        max_length=30
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    changed_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.entity_type} {self.entity_id}: {self.new_status}"