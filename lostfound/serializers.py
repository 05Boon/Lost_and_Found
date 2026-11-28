from django.utils import timezone
from rest_framework import serializers

from .models import Claim, ItemReport


class ItemReportSerializer(serializers.ModelSerializer):
    reporter = serializers.CharField(source='reporter.username', read_only=True)

    class Meta:
        model = ItemReport
        fields = [
            'id',
            'reporter',
            'report_type',
            'title',
            'description',
            'category',
            'date_lost_or_found',
            'location',
            'image',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reporter', 'status', 'created_at', 'updated_at']

    def validate_date_lost_or_found(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError('The date cannot be in the future.')
        return value

    def validate_image(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Choose an image smaller than 5 MB.')
        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        can_view_description = bool(
            user
            and user.is_authenticated
            and (
                user.is_staff
                or user.is_superuser
                or getattr(user, 'role', None) in {'staff', 'admin'}
                or instance.reporter_id == user.pk
            )
        )
        if not can_view_description:
            data.pop('description', None)
        return data


class ClaimSerializer(serializers.ModelSerializer):
    claimant = serializers.CharField(source='claimant.username', read_only=True)

    class Meta:
        model = Claim
        fields = [
            'id',
            'claimant',
            'private_evidence',
            'claim_status',
            'decision_note',
            'submitted_at',
            'decided_at',
        ]
        read_only_fields = [
            'id',
            'claimant',
            'claim_status',
            'decision_note',
            'submitted_at',
            'decided_at',
        ]
