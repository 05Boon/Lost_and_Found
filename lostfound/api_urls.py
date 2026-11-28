from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import ItemReportViewSet


router = DefaultRouter()
router.register('reports', ItemReportViewSet, basename='api-report')

urlpatterns = [
    path('', include(router.urls)),
]
