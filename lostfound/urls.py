from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_list, name='report_list'),
    path('create/', views.create_report, name='create_report'),
    path('my/', views.my_activity, name='my_activity'),
    path('report/<int:report_id>/', views.report_detail, name='report_detail'),
    path('report/<int:report_id>/edit/', views.edit_report, name='edit_report'),
    path('report/<int:report_id>/close/', views.close_report, name='close_report'),
    path('report/<int:report_id>/claim/', views.submit_claim, name='submit_claim'),
    path('claims/<int:claim_id>/respond/', views.respond_to_claim, name='respond_to_claim'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('staff/claims/', views.claim_review_queue, name='claim_review_queue'),
    path('staff/claims/<int:claim_id>/', views.review_claim, name='review_claim'),
    path(
        'staff/claims/<int:claim_id>/handover/',
        views.record_handover,
        name='record_handover',
    ),
    path('staff/reports/', views.staff_report_list, name='staff_report_list'),
    path(
        'staff/reports/<int:report_id>/status/',
        views.update_report_status,
        name='update_report_status',
    ),
]