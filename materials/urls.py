from django.urls import path
from . import views

app_name = 'materials'

urlpatterns = [
    path('student/<int:subject_id>/', views.student_materials, name='student_materials'),
    path('staff/upload/', views.staff_upload_material, name='staff_upload_material'),
    path('staff/manage/', views.staff_manage_materials, name='staff_manage_materials'),
    path('staff/delete/<int:pk>/', views.staff_delete_material, name='staff_delete_material'),
    path('panel/manage/', views.admin_manage_materials, name='admin_manage_materials'),
    path('panel/delete/<int:pk>/', views.admin_delete_material, name='admin_delete_material'),
]
