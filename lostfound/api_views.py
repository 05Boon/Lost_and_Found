from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import Claim, ItemReport, StatusHistory
from .serializers import ClaimSerializer, ItemReportSerializer


def _is_officer(user):
    return bool(
        user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or getattr(user, 'role', None) in {'staff', 'admin'}
        )
    )


class ItemReportViewSet(viewsets.ModelViewSet):
    serializer_class = ItemReportSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in {'create', 'update', 'partial_update', 'claim'}:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = ItemReport.objects.select_related('reporter')
        user = getattr(self.request, 'user', None)

        if not _is_officer(user):
            if user and user.is_authenticated:
                queryset = queryset.exclude(status='hidden').filter(
                    Q(status__in=['active', 'under review', 'matched', 'recovered', 'closed'])
                    | Q(reporter=user)
                )
            else:
                queryset = queryset.exclude(status='hidden')

        keyword = self.request.query_params.get('q', '').strip()
        category = self.request.query_params.get('category', '').strip()
        location = self.request.query_params.get('location', '').strip()
        report_type = self.request.query_params.get('report_type', '').strip()

        if keyword:
            keyword_filter = Q(title__icontains=keyword)
            if _is_officer(user):
                keyword_filter |= Q(description__icontains=keyword)
            queryset = queryset.filter(keyword_filter)
        if category in dict(ItemReport.CATEGORY_CHOICES):
            queryset = queryset.filter(category=category)
        if location:
            queryset = queryset.filter(location__icontains=location)
        if report_type in {'lost', 'found'}:
            queryset = queryset.filter(report_type=report_type)

        return queryset.order_by('-created_at')

    def retrieve(self, request, *args, **kwargs):
        report = self.get_object()
        if report.status == 'hidden':
            can_manage = report.reporter_id == request.user.pk if request.user.is_authenticated else False
            if not can_manage and not _is_officer(request.user):
                raise PermissionDenied('This report is not available.')
        return Response(ItemReportSerializer(report, context={'request': request}).data)

    def perform_create(self, serializer):
        report = serializer.save(reporter=self.request.user)
        StatusHistory.objects.create(
            entity_type='report',
            entity_id=report.pk,
            previous_status='',
            new_status=report.status,
            changed_by=self.request.user,
        )

    def partial_update(self, request, *args, **kwargs):
        report = self.get_object()
        can_manage = report.reporter_id == request.user.pk or _is_officer(request.user)
        if not can_manage:
            raise PermissionDenied('You cannot edit this report.')

        status_value = request.data.get('status')
        if 'status' in request.data and not _is_officer(request.user):
            raise PermissionDenied('Only staff can change report status.')
        if status_value and status_value not in dict(ItemReport.STATUS_CHOICES):
            raise ValidationError({'status': 'Invalid report status.'})

        serializer = self.get_serializer(report, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        previous_status = report.status
        report = serializer.save()

        if status_value and status_value in dict(ItemReport.STATUS_CHOICES):
            report.status = status_value
            report.save(update_fields=['status', 'updated_at'])
        if previous_status != report.status:
            StatusHistory.objects.create(
                entity_type='report',
                entity_id=report.pk,
                previous_status=previous_status,
                new_status=report.status,
                changed_by=request.user,
            )
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=['post'], url_path='claim')
    def claim(self, request, pk=None):
        report = self.get_object()
        if report.report_type != 'found' or report.status != 'active':
            raise ValidationError('Claims can only be submitted for active found reports.')
        if report.reporter_id == request.user.pk:
            raise ValidationError('You cannot claim an item you reported.')

        existing_claim = Claim.objects.filter(
            report=report,
            claimant=request.user,
        ).exclude(claim_status='rejected').first()
        if existing_claim:
            raise ValidationError('You already have an open claim for this item.')

        serializer = ClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = serializer.save(
            report=report,
            claimant=request.user,
        )
        StatusHistory.objects.create(
            entity_type='claim',
            entity_id=claim.pk,
            previous_status='',
            new_status=claim.claim_status,
            changed_by=request.user,
        )
        return Response(
            ClaimSerializer(claim, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )
