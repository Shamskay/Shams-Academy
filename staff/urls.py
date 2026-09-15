from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('panel/create-staff/', views.admin_create_staff, name='admin_create_staff'),
    path('panel/staff/', views.admin_staff, name='admin_staff'),
    path('panel/staff/<int:pk>/delete/', views.admin_delete_staff, name='admin_delete_staff'),
    path('panel/staff/<int:pk>/toggle-status/', views.admin_toggle_staff_status, name='admin_toggle_staff_status'),
]
