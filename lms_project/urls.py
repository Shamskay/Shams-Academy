"""
URL configuration for lms_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('materials/', include('materials.urls')),
    path('subjects/', include('subjects.urls')),
    path('students/', include('students.urls')),
    path('staff/', include('staff.urls')),
    path('assessments/', include('assessments.urls')),
    path('', include('school.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
