from django.contrib import admin
from .models import ItemReport, Claim, Handover, StatusHistory


admin.site.register(Claim)
admin.site.register(Handover)
admin.site.register(StatusHistory)

# Register your models here.
@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'title',
        'report_type',
        'category',
        'location',
        'status',
        'reporter'
    )
    list_filter = (
        'report_type',
        'category',
        'status'
    )

    search_fields = (
        'title',
        'description',
        'location'
    )