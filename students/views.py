from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.db import IntegrityError, transaction
from django.core.paginator import Paginator
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors

from accounts.models import Profile
from school.models import (
    Term, AcademicClass, Subject, ClassSubject, ClassTeacher,
    Test, Exam, TestResult, ExamResult, TermResult, PromotionDecision, AuditLog, GradeBoundary,
    Question, Option
)
from school.utils import (
    get_user_profile, get_grade_boundaries, annotate_grade, annotate_results,
    safe_float, safe_int, create_audit_log
)
from school.utils import (
    get_user_profile, get_grade_boundaries, annotate_grade, annotate_results,
    safe_float, safe_int
)


@login_required
def take_test(request, test_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')
    if profile.status != Profile.STATUS_ACTIVE:
        messages.error(request, 'Only active students can take tests.')
        return redirect('students:my_results')

    test = get_object_or_404(Test, pk=test_id, is_active=True)

    # Check if student already took this test
    existing_result = TestResult.objects.filter(student=request.user, test=test).first()
    if existing_result:
        messages.warning(request, 'You have already taken this test.')
        return redirect('students:my_results')

    questions = list(test.questions.prefetch_related('options').order_by('order'))
    if not questions:
        messages.error(request, 'This test has no questions yet.')
        return redirect('students:my_results')

    if request.method == 'POST':
        total_points = sum(q.points for q in questions)
        earned_points = 0

        for question in questions:
            selected_option_id = request.POST.get(f'question_{question.id}')
            if selected_option_id:
                try:
                    selected_option = question.options.get(pk=selected_option_id)
                    if selected_option.is_correct:
                        earned_points += question.points
                except Option.DoesNotExist:
                    pass

        # Calculate percentage score
        score_percentage = round((earned_points / total_points) * 100, 2) if total_points > 0 else 0
        # Convert to max_score scale
        score = round((earned_points / total_points) * float(test.max_score), 2) if total_points > 0 else 0

        TestResult.objects.create(
            student=request.user,
            test=test,
            score=score,
            entered_by=TestResult.ENTERED_BY_STUDENT
        )
        messages.success(request, f'Test submitted successfully. Your score: {score_percentage}%')
        return redirect('students:my_results')

    # Shuffle questions and options for display
    import random
    shuffled_questions = questions.copy()
    random.shuffle(shuffled_questions)
    for q in shuffled_questions:
        options = list(q.options.all())
        random.shuffle(options)
        q.shuffled_options = options

    context = {
        'test': test,
        'questions': shuffled_questions,
    }
    return render(request, 'students/take_test.html', context)


@login_required
def take_exam(request, exam_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')
    if profile.status != Profile.STATUS_ACTIVE:
        messages.error(request, 'Only active students can take exams.')
        return redirect('students:my_results')

    exam = get_object_or_404(Exam, pk=exam_id, is_active=True)

    # Check if student already took this exam
    existing_result = ExamResult.objects.filter(student=request.user, exam=exam).first()
    if existing_result:
        messages.warning(request, 'You have already taken this exam.')
        return redirect('students:my_results')

    questions = list(exam.questions.prefetch_related('options').order_by('order'))
    if not questions:
        messages.error(request, 'This exam has no questions yet.')
        return redirect('students:my_results')

    if request.method == 'POST':
        total_points = sum(q.points for q in questions)
        earned_points = 0

        for question in questions:
            selected_option_id = request.POST.get(f'question_{question.id}')
            if selected_option_id:
                try:
                    selected_option = question.options.get(pk=selected_option_id)
                    if selected_option.is_correct:
                        earned_points += question.points
                except Option.DoesNotExist:
                    pass

        # Calculate percentage score
        score_percentage = round((earned_points / total_points) * 100, 2) if total_points > 0 else 0
        # Convert to max_score scale
        score = round((earned_points / total_points) * float(exam.max_score), 2) if total_points > 0 else 0

        ExamResult.objects.create(
            student=request.user,
            exam=exam,
            score=score,
            entered_by=ExamResult.ENTERED_BY_STUDENT
        )
        messages.success(request, f'Exam submitted successfully. Your score: {score_percentage}%')
        return redirect('students:my_results')

    # Shuffle questions and options for display
    import random
    shuffled_questions = questions.copy()
    random.shuffle(shuffled_questions)
    for q in shuffled_questions:
        options = list(q.options.all())
        random.shuffle(options)
        q.shuffled_options = options

    context = {
        'exam': exam,
        'questions': shuffled_questions,
    }
    return render(request, 'students/take_exam.html', context)


@login_required
def student_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role != Profile.ROLE_STAFF and not request.user.is_superuser:
        if profile.status != Profile.STATUS_ACTIVE:
            messages.info(request, f'Your account status is {profile.get_status_display()}. You can view past results but cannot take new assessments.')
        current_term = Term.objects.filter(is_current=True).first()
        academic_class = profile.academic_class
        class_teacher = None
        if academic_class:
            class_teacher = ClassTeacher.objects.filter(
                academic_class=academic_class, is_active=True
            ).first()

        class_subjects = []
        if academic_class:
            class_subjects = ClassSubject.objects.filter(
                academic_class=academic_class, is_active=True
            ).select_related('subject', 'teacher')

        recent_tests = TestResult.objects.filter(
            student=request.user
        ).select_related('test', 'test__subject', 'test__term').order_by('-submitted_at')[:5]

        recent_exams = ExamResult.objects.filter(
            student=request.user
        ).select_related('exam', 'exam__subject', 'exam__term').order_by('-submitted_at')[:5]

        promotion = PromotionDecision.objects.filter(
            student=request.user
        ).select_related('term', 'from_class', 'to_class').order_by('-decided_at').first()

        context = {
            'user': request.user,
            'profile': profile,
            'current_term': current_term,
            'academic_class': academic_class,
            'class_teacher': class_teacher,
            'class_subjects': class_subjects,
            'recent_tests': recent_tests,
            'recent_exams': recent_exams,
            'promotion': promotion,
        }
        return render(request, 'students/student_dashboard.html', context)
    return redirect('school:dashboard')


@login_required
def student_subjects(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')
    if profile.status != Profile.STATUS_ACTIVE:
        messages.info(request, 'Only active students can view current term subjects and assessments.')
        return redirect('students:my_results')

    current_term = Term.objects.filter(is_current=True).first()
    academic_class = profile.academic_class

    class_subjects = []
    if academic_class:
        class_subjects = ClassSubject.objects.filter(
            academic_class=academic_class, is_active=True
        ).select_related('subject', 'teacher')

    # Get available tests and exams for current term
    tests = []
    exams = []
    if current_term and academic_class:
        tests = Test.objects.filter(
            academic_class=academic_class,
            term=current_term,
            is_active=True
        ).select_related('subject')
        exams = Exam.objects.filter(
            academic_class=academic_class,
            term=current_term,
            is_active=True
        ).select_related('subject')

    context = {
        'current_term': current_term,
        'academic_class': academic_class,
        'class_subjects': class_subjects,
        'tests': tests,
        'exams': exams,
    }
    return render(request, 'students/student_subjects.html', context)


@login_required
def my_results(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    test_results = TestResult.objects.filter(
        student=request.user
    ).select_related('test', 'test__subject', 'test__term', 'test__academic_class').order_by('-submitted_at')

    exam_results = ExamResult.objects.filter(
        student=request.user
    ).select_related('exam', 'exam__subject', 'exam__term', 'exam__academic_class').order_by('-submitted_at')

    context = {
        'test_results': test_results,
        'exam_results': exam_results,
    }
    return render(request, 'students/my_results.html', context)


@login_required
def term_results(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    term_results = TermResult.objects.filter(
        student=request.user
    ).select_related('term', 'academic_class').order_by('-term')

    promotion_decisions = PromotionDecision.objects.filter(
        student=request.user
    ).select_related('term', 'from_class', 'to_class').order_by('-term')

    boundaries = get_grade_boundaries()
    annotated_term_results = annotate_results(term_results, 'average_score', boundaries)

    context = {
        'term_results': annotated_term_results,
        'promotion_decisions': promotion_decisions,
    }
    return render(request, 'students/term_results.html', context)


@login_required
def download_term_results_pdf(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="term_results_{request.user.username}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph('Shamskay Academy - Term Results', styles['Title']))
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph(f'Student: {request.user.get_full_name() or request.user.username}', styles['Normal']))
    story.append(Paragraph(f'Admission No: {profile.admission_number}', styles['Normal']))
    if profile.academic_class:
        story.append(Paragraph(f'Class: {profile.academic_class.name}', styles['Normal']))
    story.append(Spacer(1, 8*mm))

    term_results = TermResult.objects.filter(
        student=request.user
    ).select_related('term', 'academic_class').order_by('term')

    for tr in term_results:
        story.append(Paragraph(f'<b>{tr.term.get_name_display()}</b> - Class: {tr.academic_class.name}', styles['Heading2']))
        story.append(Paragraph(f'Average Score: {tr.average_score}%', styles['Normal']))
        story.append(Paragraph(f'Total Subjects: {tr.total_subjects}', styles['Normal']))
        story.append(Spacer(1, 5*mm))

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph('Generated by Shamskay Academy LMS', styles['Normal']))

    doc.build(story)
    return response


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_students(request):
    """Admin view to list and manage student accounts.

    Displays all students grouped by academic class with their profile
    information. Superusers can update student status (active/graduated/withdrawn)
    via POST. Uses pagination to limit 25 students per page.

    GET: Display paginated student list grouped by class.
    POST: Update a student's status via profile_id and status form fields.
    """
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        new_status = request.POST.get('status')
        if profile_id and new_status in [Profile.STATUS_ACTIVE, Profile.STATUS_GRADUATED, Profile.STATUS_WITHDRAWN]:
            profile = get_object_or_404(Profile, pk=profile_id, role=Profile.ROLE_STUDENT)
            old_status = profile.status
            try:
                with transaction.atomic():
                    profile.status = new_status
                    profile.save()
                    create_audit_log(
                        user=request.user,
                        action='update',
                        model_name='Profile',
                        obj=profile,
                        changes={'status': {'old': old_status, 'new': new_status}},
                        request=request
                    )
                    messages.success(request, f'Status updated for {profile.user.get_full_name() or profile.user.username}.')
            except IntegrityError:
                messages.error(request, 'An error occurred while updating the status. Please try again.')
        else:
            messages.error(request, 'Invalid request.')
        return redirect('students:admin_students')

    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT
    ).select_related('user', 'academic_class')

    search = request.GET.get('q', '').strip()
    if search:
        students = students.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(admission_number__icontains=search) |
            Q(phone__icontains=search)
        )

    status_filter = request.GET.get('status', '').strip()
    if status_filter in [Profile.STATUS_ACTIVE, Profile.STATUS_GRADUATED, Profile.STATUS_WITHDRAWN]:
        students = students.filter(status=status_filter)

    class_filter = request.GET.get('class_id', '').strip()
    if class_filter:
        students = students.filter(academic_class_id=class_filter)

    students = students.order_by('academic_class__name', 'user__username')

    class_teachers = ClassTeacher.objects.filter(is_active=True).select_related('academic_class', 'teacher')
    class_teacher_map = {ct.academic_class_id: ct.teacher for ct in class_teachers}

    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    classes = AcademicClass.objects.filter(is_active=True).order_by('name')
    students_by_class = {}
    for cls in classes:
        students_by_class[cls] = [s for s in page_obj if s.academic_class_id == cls.pk]

    unassigned_students = [s for s in page_obj if s.academic_class_id is None]

    class_student_list = [(cls, students_by_class[cls], class_teacher_map.get(cls.pk)) for cls in classes if students_by_class[cls]]

    return render(request, 'students/admin_students.html', {
        'class_student_list': class_student_list,
        'classes': classes,
        'unassigned_students': unassigned_students,
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'class_filter': class_filter,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_student_results(request, pk):
    """Display all test and exam results for a specific student (admin view)."""
    student = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_STUDENT)
    test_results = TestResult.objects.filter(
        student=student.user
    ).select_related('test', 'test__subject', 'test__term', 'test__academic_class').order_by('-submitted_at')

    exam_results = ExamResult.objects.filter(
        student=student.user
    ).select_related('exam', 'exam__subject', 'exam__term', 'exam__academic_class').order_by('-submitted_at')

    term_results = TermResult.objects.filter(
        student=student.user
    ).select_related('term', 'academic_class').order_by('-term')
    boundaries = get_grade_boundaries()
    annotated_term_results = annotate_results(term_results, 'average_score', boundaries)

    context = {
        'student': student,
        'test_results': test_results,
        'exam_results': exam_results,
        'term_results': annotated_term_results,
    }
    return render(request, 'students/admin_student_results.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_print_student_results(request, pk):
    student = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_STUDENT)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="results_{student.user.username}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f'Results for {student.user.get_full_name() or student.user.username}', styles['Title']))
    story.append(Paragraph(f'Admission No: {student.admission_number}', styles['Normal']))
    if student.academic_class:
        story.append(Paragraph(f'Class: {student.academic_class.name}', styles['Normal']))
    story.append(Spacer(1, 10*mm))

    test_results = TestResult.objects.filter(
        student=student.user
    ).select_related('test', 'test__subject', 'test__term').order_by('-submitted_at')

    exam_results = ExamResult.objects.filter(
        student=student.user
    ).select_related('exam', 'exam__subject', 'exam__term').order_by('-submitted_at')

    if test_results:
        story.append(Paragraph('Test Results', styles['Heading2']))
        for tr in test_results:
            story.append(Paragraph(f'{tr.test.title} ({tr.test.subject.code}): {tr.score}/{tr.test.max_score} ({tr.get_percentage}%)', styles['Normal']))
        story.append(Spacer(1, 5*mm))

    if exam_results:
        story.append(Paragraph('Exam Results', styles['Heading2']))
        for er in exam_results:
            story.append(Paragraph(f'{er.exam.title} ({er.exam.subject.code}): {er.score}/{er.exam.max_score} ({er.get_percentage}%)', styles['Normal']))

    doc.build(story)
    return response


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_student(request, pk):
    if request.method != 'POST':
        return redirect('students:admin_students')
    profile = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_STUDENT)
    try:
        user = profile.user
        profile_repr = str(profile)
        profile.delete()
        user.delete()
        create_audit_log(
            user=request.user,
            action='delete',
            model_name='Profile',
            object_id=str(pk),
            object_repr=profile_repr,
            request=request
        )
        messages.success(request, 'Student removed successfully.')
    except IntegrityError:
        messages.error(request, 'Cannot delete this student because they have related assessment records. Remove them first.')
    return redirect('students:admin_students')


from staff.decorators import staff_required


@staff_required
def staff_manage_students(request):
    class_teachers = ClassTeacher.objects.filter(
        teacher=request.user, is_active=True
    ).select_related('academic_class')
    classes = [ct.academic_class for ct in class_teachers]

    if not classes:
        messages.error(request, 'You are not assigned as a class teacher.')
        return redirect('staff:staff_dashboard')

    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT,
        academic_class__in=classes
    ).select_related('user', 'academic_class').order_by('academic_class__name', 'user__username')

    unassigned_students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT,
        academic_class__isnull=True
    ).select_related('user').order_by('user__username')

    context = {
        'classes': classes,
        'students': students,
        'unassigned_students': unassigned_students,
    }
    return render(request, 'students/staff_manage_students.html', context)


@staff_required
def staff_class_results(request, pk):
    academic_class = get_object_or_404(AcademicClass, pk=pk)
    if not ClassTeacher.objects.filter(
        teacher=request.user, academic_class=academic_class, is_active=True
    ).exists():
        messages.error(request, 'You are not the class teacher for this class.')
        return redirect('staff:staff_dashboard')

    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT,
        academic_class=academic_class
    ).select_related('user').order_by('user__username')

    class_subjects = ClassSubject.objects.filter(
        academic_class=academic_class, is_active=True
    ).select_related('subject')
    subjects = Subject.objects.filter(
        pk__in=class_subjects.values_list('subject_id', flat=True)
    ).order_by('code')

    boundaries = get_grade_boundaries()
    student_results = []
    for student in students:
        student_test_results = TestResult.objects.filter(
            student=student.user,
            test__academic_class=academic_class
        ).select_related('test', 'test__subject').order_by('-submitted_at')
        student_exam_results = ExamResult.objects.filter(
            student=student.user,
            exam__academic_class=academic_class
        ).select_related('exam', 'exam__subject').order_by('-submitted_at')

        subject_data = []
        for subject in subjects:
            tr = student_test_results.filter(test__subject=subject).first()
            er = student_exam_results.filter(exam__subject=subject).first()
            max_total = 0
            total_score = 0
            percentage = 0
            if tr:
                total_score += float(tr.score)
                max_total += float(tr.test.max_score)
            if er:
                total_score += float(er.score)
                max_total += float(er.exam.max_score)
            if max_total > 0:
                percentage = round(max(0, (total_score / max_total) * 100), 2)
            grade = annotate_grade(None, percentage, boundaries)
            subject_data.append({
                'subject': subject,
                'test_result': tr,
                'exam_result': er,
                'total_score': int(round(total_score)) if total_score > 0 else None,
                'max_total': int(round(max_total)) if max_total > 0 else None,
                'percentage': percentage,
                'grade': grade,
            })

        student_results.append({
            'student': student,
            'subjects': subject_data,
        })

    context = {
        'academic_class': academic_class,
        'student_results': student_results,
    }
    return render(request, 'students/staff_class_results.html', context)


@staff_required
def staff_student_results(request, class_pk, student_pk):
    """Display results for a specific student in a class teacher's class."""
    academic_class = get_object_or_404(AcademicClass, pk=class_pk)
    if not ClassTeacher.objects.filter(
        teacher=request.user, academic_class=academic_class, is_active=True
    ).exists():
        messages.error(request, 'You are not the class teacher for this class.')
        return redirect('staff:staff_dashboard')

    student = get_object_or_404(Profile, pk=student_pk, role=Profile.ROLE_STUDENT, academic_class=academic_class)

    class_subjects = ClassSubject.objects.filter(
        academic_class=academic_class, is_active=True
    ).select_related('subject')
    subjects = Subject.objects.filter(
        pk__in=class_subjects.values_list('subject_id', flat=True)
    ).order_by('code')

    boundaries = get_grade_boundaries()
    subject_data = []
    for subject in subjects:
        tr = TestResult.objects.filter(
            student=student.user,
            test__academic_class=academic_class,
            test__subject=subject
        ).select_related('test', 'test__subject', 'test__term').order_by('-submitted_at').first()
        
        er = ExamResult.objects.filter(
            student=student.user,
            exam__academic_class=academic_class,
            exam__subject=subject
        ).select_related('exam', 'exam__subject', 'exam__term').order_by('-submitted_at').first()

        max_total = 0
        total_score = 0
        percentage = 0
        if tr:
            total_score += float(tr.score)
            max_total += float(tr.test.max_score)
        if er:
            total_score += float(er.score)
            max_total += float(er.exam.max_score)
        if max_total > 0:
            percentage = round(max(0, (total_score / max_total) * 100), 2)
        grade = annotate_grade(None, percentage, boundaries)
        subject_data.append({
            'subject': subject,
            'test_result': tr,
            'exam_result': er,
            'total_score': int(round(total_score)) if total_score > 0 else None,
            'max_total': int(round(max_total)) if max_total > 0 else None,
            'percentage': percentage,
            'grade': grade,
        })

    test_results = TestResult.objects.filter(
        student=student.user,
        test__academic_class=academic_class
    ).select_related('test', 'test__subject', 'test__term').order_by('-submitted_at')

    exam_results = ExamResult.objects.filter(
        student=student.user,
        exam__academic_class=academic_class
    ).select_related('exam', 'exam__subject', 'exam__term').order_by('-submitted_at')

    term_results = TermResult.objects.filter(
        student=student.user,
        academic_class=academic_class
    ).select_related('term').order_by('-term')
    annotated_term_results = annotate_results(term_results, 'average_score', boundaries)

    context = {
        'academic_class': academic_class,
        'student': student,
        'subject_data': subject_data,
        'test_results': test_results,
        'exam_results': exam_results,
        'term_results': annotated_term_results,
    }
    return render(request, 'students/staff_student_results.html', context)


@staff_required
def staff_subject_students(request):
    teaching_assignments = ClassSubject.objects.filter(
        teacher=request.user, is_active=True
    ).select_related('subject', 'academic_class').order_by('academic_class__name')

    class_data = {}
    for assignment in teaching_assignments:
        cls = assignment.academic_class
        if cls not in class_data:
            class_data[cls] = {'subjects': set(), 'students': []}
        class_data[cls]['subjects'].add(assignment.subject)

    for cls in class_data:
        students = Profile.objects.filter(
            role=Profile.ROLE_STUDENT,
            academic_class=cls
        ).select_related('user').order_by('user__username')
        for student in students:
            class_data[cls]['students'].append({
                'student': student,
                'subjects': list(class_data[cls]['subjects']),
            })

    context = {
        'class_data': [
            {
                'class': cls,
                'subjects': list(data['subjects']),
                'students': data['students'],
            }
            for cls, data in class_data.items()
        ],
    }
    return render(request, 'students/staff_subject_students.html', context)
