from django.urls import path
from . import views

app_name = 'assessments'

urlpatterns = [
    path('staff/enter-test-result/', views.staff_enter_test_result, name='staff_enter_test_result'),
    path('staff/enter-exam-result/', views.staff_enter_exam_result, name='staff_enter_exam_result'),
    path('staff/enter-results/', views.staff_enter_results_table, name='staff_enter_results_table'),
    path('panel/calculate-term-results/', views.admin_calculate_term_results, name='admin_calculate_term_results'),
    path('panel/promote-students/', views.admin_promote_students, name='admin_promote_students'),
    path('panel/manage-tests/', views.admin_manage_tests, name='admin_manage_tests'),
    path('panel/manage-exams/', views.admin_manage_exams, name='admin_manage_exams'),
    path('panel/test/<int:pk>/questions/', views.admin_view_test_questions, name='admin_view_test_questions'),
    path('panel/exam/<int:pk>/questions/', views.admin_view_exam_questions, name='admin_view_exam_questions'),
    path('staff/create-test/', views.staff_create_test, name='staff_create_test'),
    path('staff/manage-tests/', views.staff_manage_tests, name='staff_manage_tests'),
    path('staff/tests/<int:pk>/delete/', views.staff_delete_test, name='staff_delete_test'),
    path('staff/create-exam/', views.staff_create_exam, name='staff_create_exam'),
    path('staff/manage-exams/', views.staff_manage_exams, name='staff_manage_exams'),
    path('staff/exams/<int:pk>/delete/', views.staff_delete_exam, name='staff_delete_exam'),

    # Question management
    path('staff/test/<int:assessment_id>/questions/', views.staff_manage_questions, {'assessment_type': 'test'}, name='staff_manage_test_questions'),
    path('staff/test/<int:assessment_id>/questions/add/', views.staff_add_question, {'assessment_type': 'test'}, name='staff_add_test_question'),
    path('staff/test/<int:assessment_id>/questions/<int:question_id>/edit/', views.staff_edit_question, {'assessment_type': 'test'}, name='staff_edit_test_question'),
    path('staff/test/<int:assessment_id>/questions/<int:question_id>/delete/', views.staff_delete_question, {'assessment_type': 'test'}, name='staff_delete_test_question'),

    path('staff/exam/<int:assessment_id>/questions/', views.staff_manage_questions, {'assessment_type': 'exam'}, name='staff_manage_exam_questions'),
    path('staff/exam/<int:assessment_id>/questions/add/', views.staff_add_question, {'assessment_type': 'exam'}, name='staff_add_exam_question'),
    path('staff/exam/<int:assessment_id>/questions/<int:question_id>/edit/', views.staff_edit_question, {'assessment_type': 'exam'}, name='staff_edit_exam_question'),
    path('staff/exam/<int:assessment_id>/questions/<int:question_id>/delete/', views.staff_delete_question, {'assessment_type': 'exam'}, name='staff_delete_exam_question'),
]
