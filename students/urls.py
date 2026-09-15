from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student/subjects/', views.student_subjects, name='student_subjects'),
    path('student/test/<int:test_id>/take/', views.take_test, name='take_test'),
    path('student/exam/<int:exam_id>/take/', views.take_exam, name='take_exam'),
    path('student/results/', views.my_results, name='my_results'),
    path('student/term-results/', views.term_results, name='term_results'),
    path('student/term-results/download/', views.download_term_results_pdf, name='download_term_results_pdf'),
    path('panel/students/', views.admin_students, name='admin_students'),
    path('panel/students/<int:pk>/results/', views.admin_student_results, name='admin_student_results'),
    path('panel/students/<int:pk>/results/print/', views.admin_print_student_results, name='admin_print_student_results'),
    path('panel/students/<int:pk>/delete/', views.admin_delete_student, name='admin_delete_student'),
    path('staff/manage-students/', views.staff_manage_students, name='staff_manage_students'),
    path('staff/class/<int:pk>/results/', views.staff_class_results, name='staff_class_results'),
    path('staff/class/<int:class_pk>/student/<int:student_pk>/results/', views.staff_student_results, name='staff_student_results'),
    path('staff/subject-students/', views.staff_subject_students, name='staff_subject_students'),
]
