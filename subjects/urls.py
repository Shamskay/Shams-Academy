from django.urls import path
from . import views

app_name = 'subjects'

urlpatterns = [
    path('panel/terms/', views.admin_terms, name='admin_terms'),
    path('panel/classes/', views.admin_classes, name='admin_classes'),
    path('panel/subjects/', views.admin_subjects, name='admin_subjects'),
    path('panel/subjects/<int:pk>/edit/', views.admin_edit_subject, name='admin_edit_subject'),
    path('panel/subjects/<int:pk>/delete/', views.admin_delete_subject, name='admin_delete_subject'),
    path('panel/class-subjects/', views.admin_class_subjects, name='admin_class_subjects'),
    path('panel/class-teachers/', views.admin_class_teachers, name='admin_class_teachers'),
    path('panel/class-teachers/<int:pk>/remove/', views.admin_remove_class_teacher, name='admin_remove_class_teacher'),
    path('panel/class-teachers/<int:pk>/toggle/', views.admin_toggle_class_teacher, name='admin_toggle_class_teacher'),
    path('panel/class-subjects/<int:pk>/toggle/', views.admin_toggle_class_subject, name='admin_toggle_class_subject'),
]
