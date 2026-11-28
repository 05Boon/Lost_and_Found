from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ClaimForm,
    ClaimReviewForm,
    HandoverForm,
    ItemReportForm,
    StaffReportStatusForm,
)
from .models import Claim, Handover, ItemReport, StatusHistory


def _is_officer(user):
    return bool(
        user.is_authenticated
        and (
            user.is_staff
            or user.is_superuser
            or getattr(user, 'role', None) in {'staff', 'admin'}
        )
    )


def _record_status_change(entity_type, entity, previous_status, new_status, user):
    if previous_status == new_status:
        return
    StatusHistory.objects.create(
        entity_type=entity_type,
        entity_id=entity.pk,
        previous_status=previous_status or '',
        new_status=new_status,
        changed_by=user,
    )


def landing(request):
    active_reports = ItemReport.objects.filter(status='active')
    return render(request, 'lostfound/landing.html', {
        'lost_count': active_reports.filter(report_type='lost').count(),
        'found_count': active_reports.filter(report_type='found').count(),
    })


def _item_reports(request, report_type):
    reports = ItemReport.objects.filter(status='active', report_type=report_type)
    can_view_description = _is_officer(request.user)

    keyword = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    location = request.GET.get('location', '').strip()
    if keyword:
        keyword_filter = Q(title__icontains=keyword)
        if can_view_description:
            keyword_filter |= Q(description__icontains=keyword)
        reports = reports.filter(keyword_filter)
    if category in dict(ItemReport.CATEGORY_CHOICES):
        reports = reports.filter(category=category)
    if location:
        reports = reports.filter(location__icontains=location)

    reports = reports.select_related('reporter').order_by('-created_at')
    report_page = Paginator(reports, 12).get_page(request.GET.get('page'))
    return render(request, 'lostfound/item_reports.html', {
        'reports': report_page,
        'report_type': report_type,
        'page_title': 'Lost reports' if report_type == 'lost' else 'Found reports',
        'page_intro': (
            'Search items reported missing and see whether one may belong to you.'
            if report_type == 'lost'
            else 'Browse items found by the community and submit a private claim.'
        ),
        'categories': ItemReport.CATEGORY_CHOICES,
        'can_view_description': can_view_description,
    })


def lost_reports(request):
    return _item_reports(request, 'lost')


def found_reports(request):
    return _item_reports(request, 'found')


def report_list(request):
    return lost_reports(request)


@login_required
def create_report(request):
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            _record_status_change('report', report, '', report.status, request.user)
            messages.success(request, 'Your report is now visible in the community listings.')
            return redirect('report_detail', report_id=report.pk)
    else:
        form = ItemReportForm()

    return render(request, 'lostfound/create_report.html', {'form': form})


def report_detail(request, report_id):
    report = get_object_or_404(
        ItemReport.objects.select_related('reporter'),
        pk=report_id,
    )
    is_staff_user = _is_officer(request.user)
    can_manage = request.user.is_authenticated and (
        request.user.pk == report.reporter_id or is_staff_user
    )
    if report.status == 'hidden' and not can_manage:
        from django.http import Http404
        raise Http404

    existing_claim = None
    if request.user.is_authenticated and report.report_type == 'found':
        existing_claim = Claim.objects.filter(
            report=report,
            claimant=request.user,
        ).exclude(claim_status='rejected').first()

    opposite_type = 'found' if report.report_type == 'lost' else 'lost'
    match_suggestions = ItemReport.objects.none()
    if report.status == 'active':
        match_suggestions = (
            ItemReport.objects.filter(
                status='active',
                category=report.category,
                report_type=opposite_type,
            )
            .exclude(pk=report.pk)
            .order_by('-created_at')[:4]
        )

    return render(request, 'lostfound/report_detail.html', {
        'report': report,
        'can_manage': can_manage,
        'can_claim': (
            request.user.is_authenticated
            and report.report_type == 'found'
            and report.status == 'active'
            and report.reporter_id != request.user.pk
            and existing_claim is None
        ),
        'existing_claim': existing_claim,
        'can_view_description': is_staff_user,
        'match_suggestions': match_suggestions,
        'status_history': (
            StatusHistory.objects.filter(entity_type='report', entity_id=report.pk)
            .select_related('changed_by')
            .order_by('-changed_at')[:10]
            if can_manage else []
        ),
        'has_handover': report.handovers.exists(),
        'approved_claims': (
            report.claims.filter(claim_status='approved').select_related('claimant')
            if is_staff_user else []
        ),
    })


@login_required
def submit_claim(request, report_id):
    report = get_object_or_404(
        ItemReport,
        pk=report_id,
        report_type='found',
        status='active',
    )
    if report.reporter_id == request.user.pk:
        messages.error(request, 'You cannot claim an item you reported.')
        return redirect('report_detail', report_id=report.pk)

    existing_claim = Claim.objects.filter(
        report=report,
        claimant=request.user,
    ).exclude(claim_status='rejected').first()
    if existing_claim:
        messages.info(request, 'You already have an open claim for this item.')
        return redirect('my_activity')

    if request.method == 'POST':
        form = ClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.report = report
            claim.claimant = request.user
            claim.save()
            _record_status_change('claim', claim, '', claim.claim_status, request.user)
            messages.success(request, 'Your claim was sent privately to the review team.')
            return redirect('my_activity')
    else:
        form = ClaimForm()

    return render(request, 'lostfound/submit_claim.html', {
        'form': form,
        'report': report,
    })


@login_required
def respond_to_claim(request, claim_id):
    claim = get_object_or_404(
        Claim.objects.select_related('report'),
        pk=claim_id,
        claimant=request.user,
        claim_status='more_info',
    )
    if request.method == 'POST':
        form = ClaimForm(request.POST, instance=claim)
        if form.is_valid():
            previous_status = claim.claim_status
            claim = form.save(commit=False)
            claim.claim_status = 'pending'
            claim.decision_note = ''
            claim.decided_at = None
            claim.reviewer = None
            claim.save()
            _record_status_change(
                'claim', claim, previous_status, claim.claim_status, request.user
            )
            messages.success(request, 'Your additional information was sent for review.')
            return redirect('my_activity')
    else:
        form = ClaimForm(instance=claim)
    return render(request, 'lostfound/respond_to_claim.html', {
        'form': form,
        'claim': claim,
    })


@login_required
def my_activity(request):
    reports = (
        ItemReport.objects.filter(reporter=request.user)
        .annotate(claim_count=Count('claims'))
        .order_by('-updated_at')
    )
    claims = (
        Claim.objects.filter(claimant=request.user)
        .select_related('report')
        .order_by('-submitted_at')
    )
    return render(request, 'lostfound/my_activity.html', {
        'reports': reports,
        'claims': claims,
    })


@login_required
def edit_report(request, report_id):
    report = get_object_or_404(
        ItemReport,
        pk=report_id,
        reporter=request.user,
        status__in=['active', 'under review'],
    )
    if request.method == 'POST':
        form = ItemReportForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your report was updated.')
            return redirect('report_detail', report_id=report.pk)
    else:
        form = ItemReportForm(instance=report)
    return render(request, 'lostfound/edit_report.html', {
        'form': form,
        'report': report,
    })


@login_required
@require_POST
def close_report(request, report_id):
    report = get_object_or_404(
        ItemReport,
        pk=report_id,
        reporter=request.user,
        status__in=['active', 'under review'],
    )
    previous_status = report.status
    report.status = 'closed'
    report.save(update_fields=['status', 'updated_at'])
    _record_status_change('report', report, previous_status, report.status, request.user)
    messages.success(request, 'Your report is closed and no longer appears in search.')
    return redirect('my_activity')


@staff_member_required(login_url='admin:login')
def admin_dashboard(request):
    context = {
        'total_reports': ItemReport.objects.count(),
        'lost_reports': ItemReport.objects.filter(report_type='lost').count(),
        'found_reports': ItemReport.objects.filter(report_type='found').count(),
        'pending_claims': Claim.objects.filter(
            claim_status__in=['pending', 'more_info']
        ).count(),
        'reports_by_status': (
            ItemReport.objects.values('status').annotate(total=Count('id')).order_by('status')
        ),
        'recent_reports': ItemReport.objects.select_related('reporter').order_by(
            '-created_at'
        )[:6],
        'recent_claims': Claim.objects.select_related(
            'report', 'claimant'
        ).order_by('-submitted_at')[:6],
    }
    return render(request, 'lostfound/admin_dashboard.html', context)


@staff_member_required(login_url='admin:login')
def claim_review_queue(request):
    status = request.GET.get('status', 'open')
    claims = Claim.objects.select_related('report', 'claimant', 'reviewer')
    valid_statuses = dict(Claim.CLAIM_STATUS)
    if status == 'open':
        claims = claims.filter(claim_status__in=['pending', 'more_info'])
    elif status in valid_statuses:
        claims = claims.filter(claim_status=status)
    else:
        status = 'open'
        claims = claims.filter(claim_status__in=['pending', 'more_info'])
    return render(request, 'lostfound/claim_queue.html', {
        'claims': claims.order_by('-submitted_at'),
        'selected_status': status,
        'claim_statuses': Claim.CLAIM_STATUS,
    })


@staff_member_required(login_url='admin:login')
def review_claim(request, claim_id):
    claim = get_object_or_404(
        Claim.objects.select_related('report', 'claimant'),
        pk=claim_id,
    )
    if claim.claim_status == 'approved':
        if request.method == 'POST':
            messages.info(request, 'This claim is approved and cannot be changed here.')
            return redirect('review_claim', claim_id=claim.pk)
        return render(request, 'lostfound/review_claim.html', {
            'claim': claim,
            'form': None,
        })

    if request.method == 'POST':
        form = ClaimReviewForm(request.POST, instance=claim)
        if form.is_valid():
            new_status = form.cleaned_data['claim_status']
            approval_error = ''
            with transaction.atomic():
                claim = Claim.objects.select_for_update().get(pk=claim.pk)
                report = None
                if new_status == 'approved':
                    report = ItemReport.objects.select_for_update().get(
                        pk=claim.report_id
                    )
                    another_approved_claim_exists = Claim.objects.filter(
                        report=report,
                        claim_status='approved',
                    ).exclude(pk=claim.pk).exists()
                    if report.status not in {'active', 'matched'}:
                        approval_error = (
                            'This report is no longer active, so this claim cannot be approved.'
                        )
                    elif another_approved_claim_exists:
                        approval_error = (
                            'Another claim has already been approved for this item.'
                        )

                if approval_error:
                    messages.error(request, approval_error)
                    return redirect('review_claim', claim_id=claim.pk)

                previous_status = claim.claim_status
                claim.claim_status = new_status
                claim.decision_note = form.cleaned_data['decision_note']
                claim.reviewer = request.user
                claim.decided_at = timezone.now()
                claim.save(update_fields=[
                    'claim_status', 'decision_note', 'reviewer', 'decided_at',
                ])
                _record_status_change(
                    'claim', claim, previous_status, claim.claim_status, request.user
                )

                if new_status == 'approved':
                    previous_report_status = report.status
                    if report.status == 'active':
                        report.status = 'matched'
                        report.save(update_fields=['status', 'updated_at'])
                        _record_status_change(
                            'report',
                            report,
                            previous_report_status,
                            report.status,
                            request.user,
                        )

                    other_claims = Claim.objects.filter(
                        report=report,
                        claim_status__in=['pending', 'more_info'],
                    ).exclude(pk=claim.pk)
                    for other_claim in other_claims:
                        previous_claim_status = other_claim.claim_status
                        other_claim.claim_status = 'rejected'
                        other_claim.decision_note = (
                            'Another ownership claim was approved for this item.'
                        )
                        other_claim.reviewer = request.user
                        other_claim.decided_at = timezone.now()
                        other_claim.save(update_fields=[
                            'claim_status', 'decision_note', 'reviewer', 'decided_at',
                        ])
                        _record_status_change(
                            'claim',
                            other_claim,
                            previous_claim_status,
                            other_claim.claim_status,
                            request.user,
                        )

            messages.success(request, 'The claim decision was saved.')
            return redirect('claim_review_queue')
    else:
        form = ClaimReviewForm(instance=claim)

    return render(request, 'lostfound/review_claim.html', {
        'claim': claim,
        'form': form,
    })


@staff_member_required(login_url='admin:login')
def staff_report_list(request):
    reports = ItemReport.objects.select_related('reporter')
    status = request.GET.get('status', '')
    report_type = request.GET.get('type', '')
    keyword = request.GET.get('q', '').strip()

    if status in dict(ItemReport.STATUS_CHOICES):
        reports = reports.filter(status=status)
    if report_type in dict(ItemReport.REPORT_TYPES):
        reports = reports.filter(report_type=report_type)
    if keyword:
        reports = reports.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(location__icontains=keyword)
        )

    page_obj = Paginator(reports.order_by('-updated_at'), 20).get_page(
        request.GET.get('page')
    )
    return render(request, 'lostfound/staff_reports.html', {
        'reports': page_obj,
        'page_obj': page_obj,
        'status_choices': ItemReport.STATUS_CHOICES,
        'status_edit_choices': [
            choice for choice in ItemReport.STATUS_CHOICES
            if choice[0] != 'recovered'
        ],
        'selected_status': status,
        'selected_type': report_type,
        'query': keyword,
    })


@staff_member_required(login_url='admin:login')
@require_POST
def update_report_status(request, report_id):
    report = get_object_or_404(ItemReport, pk=report_id)
    form = StaffReportStatusForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Choose a valid report status.')
        return redirect('staff_report_list')
    new_status = form.cleaned_data['status']
    if new_status == 'recovered':
        messages.error(request, 'Record a handover before marking an item recovered.')
        return redirect('staff_report_list')

    previous_status = report.status
    report.status = new_status
    report.save(update_fields=['status', 'updated_at'])
    _record_status_change('report', report, previous_status, report.status, request.user)
    messages.success(request, f'Report status changed to {report.get_status_display()}.')
    return redirect('staff_report_list')


@staff_member_required(login_url='admin:login')
def record_handover(request, claim_id):
    claim = get_object_or_404(
        Claim.objects.select_related('report', 'claimant'),
        pk=claim_id,
        claim_status='approved',
    )
    if Handover.objects.filter(claim=claim).exists():
        messages.info(request, 'A handover has already been recorded for this claim.')
        return redirect('report_detail', report_id=claim.report_id)
    if claim.report.status != 'matched':
        messages.error(request, 'The report must be matched before recording a handover.')
        return redirect('report_detail', report_id=claim.report_id)

    if request.method == 'POST':
        form = HandoverForm(request.POST)
        if form.is_valid():
            duplicate_handover = False
            invalid_report_status = False
            with transaction.atomic():
                claim = Claim.objects.select_for_update().get(
                    pk=claim.pk,
                    claim_status='approved',
                )
                report = ItemReport.objects.select_for_update().get(
                    pk=claim.report_id
                )
                duplicate_handover = Handover.objects.filter(claim=claim).exists()
                invalid_report_status = report.status != 'matched'
                if duplicate_handover or invalid_report_status:
                    if duplicate_handover:
                        messages.info(
                            request,
                            'A handover has already been recorded for this claim.',
                        )
                    else:
                        messages.error(
                            request,
                            'The report must be matched before recording a handover.',
                        )
                    return redirect('report_detail', report_id=claim.report_id)

                handover = form.save(commit=False)
                handover.report = claim.report
                handover.claim = claim
                handover.recorded_by = request.user
                handover.handover_date = timezone.now()
                handover.save()
                previous_status = report.status
                report.status = 'recovered'
                report.save(update_fields=['status', 'updated_at'])
                _record_status_change(
                    'report', report, previous_status, report.status, request.user
                )
            messages.success(request, 'The handover was recorded and the report is recovered.')
            return redirect('report_detail', report_id=claim.report_id)
    else:
        form = HandoverForm()
    return render(request, 'lostfound/handover_form.html', {
        'form': form,
        'claim': claim,
    })
