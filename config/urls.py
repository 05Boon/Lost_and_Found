from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from lostfound.views import landing
from lostfound import views as lostfound_views
urlpatterns = [

    path('admin/', admin.site.urls),

    path('', landing, name='landing'),

    path('lost/', lostfound_views.lost_reports, name='lost_reports'),
    path('found/', lostfound_views.found_reports, name='found_reports'),

    path('browse/', include('lostfound.urls')),

    path('browse/', include('lostfound.urls')),

    path('accounts/', include('accounts.urls')),

    path('accounts/', include('django.contrib.auth.urls')),

    path('api/', include('lostfound.api_urls')),
    path('api/auth/', include('accounts.api_urls')),

]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )