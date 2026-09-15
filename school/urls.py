from django.urls import path
from . import views

app_name = 'school'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('panel/create-student/', views.admin_create_student, name='admin_create_student'),
    path('panel/create-parent/', views.admin_create_parent, name='admin_create_parent'),
    path('panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel/all-results/', views.admin_all_results, name='admin_all_results'),
    path('panel/classes/<int:pk>/delete/', views.admin_delete_class, name='admin_delete_class'),
    path('panel/grade-boundaries/', views.admin_grade_boundaries, name='admin_grade_boundaries'),
    path('panel/grade-boundaries/<int:pk>/delete/', views.admin_delete_grade_boundary, name='admin_delete_grade_boundary'),
    path('panel/result-remarks/', views.admin_result_remarks, name='admin_result_remarks'),
    path('panel/result-remarks/<int:pk>/delete/', views.admin_delete_result_remark, name='admin_delete_result_remark'),
    path('panel/generate-report-cards/', views.admin_generate_report_cards, name='admin_generate_report_cards'),
    path('student/report-card/', views.report_card, name='report_card'),
    path('panel/parent-profiles/', views.admin_parent_profiles, name='admin_parent_profiles'),
    path('panel/parent-profiles/<int:pk>/delete/', views.admin_delete_parent_profile, name='admin_delete_parent_profile'),
    path('panel/parent-profiles/<int:parent_id>/add-child/', views.admin_add_child_to_parent, name='admin_add_child_to_parent'),
    path('panel/events/', views.admin_events, name='admin_events'),
    path('panel/events/<int:pk>/delete/', views.admin_delete_event, name='admin_delete_event'),
    path('panel/fees/', views.admin_fees, name='admin_fees'),
    path('panel/fees/<int:pk>/delete/', views.admin_delete_fee, name='admin_delete_fee'),
    path('panel/payments/', views.admin_payments, name='admin_payments'),
    path('panel/payments/<int:pk>/delete/', views.admin_delete_payment, name='admin_delete_payment'),
    path('panel/audit-logs/', views.admin_audit_logs, name='admin_audit_logs'),
    path('panel/export/students/', views.admin_export_students_csv, name='admin_export_students_csv'),
    path('panel/export/results/', views.admin_export_results_csv, name='admin_export_results_csv'),
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),
    path('parent/child/<int:student_id>/', views.parent_child_detail, name='parent_child_detail'),
]
