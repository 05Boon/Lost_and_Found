from django import forms
from django.utils import timezone

from .models import Claim, ItemReport, Handover


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            css_class = 'form-select' if isinstance(widget, forms.Select) else 'form-control'
            widget.attrs['class'] = f'{widget.attrs.get("class", "")} {css_class}'.strip()


class ItemReportForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ItemReport
        fields = [
            'report_type',
            'title',
            'description',
            'category',
            'date_lost_or_found',
            'location',
            'image',
        ]
        labels = {
            'image': 'Photo (optional)',
        }
        help_texts = {
            'report_type': 'Choose whether you lost an item or found one.',
            'title': 'Use a short description that will help people recognize it.',
            'description': 'Include visible details such as color, brand, and condition. Keep proof of ownership private.',
            'category': 'Choose the closest match.',
            'date_lost_or_found': 'Choose the day you last saw it or found it. Future dates are not accepted.',
            'location': 'Be as specific as you can, such as a building, floor, or nearby landmark.',
            'image': 'Add a clear photo if you have one. Images must be smaller than 5 MB.',
        }
        widgets = {
            'report_type': forms.Select(),
            'category': forms.Select(),
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g. Blue backpack with a keychain',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe identifying details without sharing private proof of ownership.',
            }),
            'date_lost_or_found': forms.DateInput(attrs={'type': 'date'}),
            'location': forms.TextInput(attrs={
                'placeholder': 'e.g. Main library, second floor',
            }),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_lost_or_found'].widget.attrs['max'] = timezone.localdate().isoformat()
        for name, field in self.fields.items():
            bound_field = self[name]
            widget = field.widget
            widget.attrs['aria-describedby'] = (
                f'{bound_field.auto_id}_help {bound_field.auto_id}_errors'
            )
            if self.is_bound and bound_field.errors:
                widget.attrs['aria-invalid'] = 'true'
                widget.attrs['class'] += ' is-invalid'

    def clean_date_lost_or_found(self):
        date = self.cleaned_data['date_lost_or_found']
        if date > timezone.localdate():
            raise forms.ValidationError('The date cannot be in the future.')
        return date

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Choose an image smaller than 5 MB.')
        return image


class ClaimForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['private_evidence']
        labels = {'private_evidence': 'How can you identify this item?'}
        help_texts = {
            'private_evidence': 'Only authorized staff can review this information. Do not include passwords or other account credentials.',
        }
        widgets = {
            'private_evidence': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Share details that only the owner would know, such as distinguishing marks or what was inside.',
            }),
        }


class ClaimReviewForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Claim
        fields = ['claim_status', 'decision_note']
        labels = {
            'claim_status': 'Decision',
            'decision_note': 'Note for the claimant',
        }
        widgets = {
            'decision_note': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Explain what happens next or what additional information is needed.',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['claim_status'].choices = [
            choice for choice in Claim.CLAIM_STATUS if choice[0] != 'pending'
        ]

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('claim_status')
        note = (cleaned_data.get('decision_note') or '').strip()
        if status in {'more_info', 'rejected'} and not note:
            self.add_error(
                'decision_note',
                'Add a note explaining this decision.',
            )
        return cleaned_data


class StaffReportStatusForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(
        choices=[
            choice for choice in ItemReport.STATUS_CHOICES
            if choice[0] != 'recovered'
        ],
        label='Report status',
    )


class HandoverForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Handover
        fields = ['outcome', 'notes']
        labels = {
            'outcome': 'Handover outcome',
            'notes': 'Additional notes',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
