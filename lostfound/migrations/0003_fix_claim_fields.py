# Manual migration to fix Claim model fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lostfound', '0002_claim_handover_statushistory'),
    ]

    operations = [
        # Add the missing claim_status field
        migrations.AddField(
            model_name='claim',
            name='claim_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('more_info', 'More Information Required'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        # Change private_evidence from CharField to TextField
        migrations.AlterField(
            model_name='claim',
            name='private_evidence',
            field=models.TextField(),
        ),
        # Update claim_status choices display for more_info
        migrations.AlterField(
            model_name='claim',
            name='claim_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('more_info', 'More Information Required'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        # Change reviewer on_delete from CASCADE to SET_NULL
        migrations.AlterField(
            model_name='claim',
            name='reviewer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reviewed_claims',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
