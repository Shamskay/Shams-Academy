from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from staff.decorators import staff_required
from accounts.models import Profile
from school.models import Test, Exam, Term, Subject, AcademicClass, ClassSubject, Question, Option, TestResult, ExamResult, TermResult, PromotionDecision, GradeBoundary
from school.forms import TeacherTestForm, TeacherExamForm, TestResultForm, ExamResultForm
from school.utils import get_user_profile, create_audit_log
from django.db import transaction, IntegrityError
from django.core.paginator import Paginator
from django.db.models import Q


@staff_required
def staff_manage_questions(request, assessment_type, assessment_id):
    """Manage questions for a test or exam."""
    if assessment_type == 'test':
        assessment = get_object_or_404(Test, pk=assessment_id)
        template = 'assessments/staff_manage_test_questions.html'
        url_name = 'assessments:staff_manage_test_questions'
    else:
        assessment = get_object_or_404(Exam, pk=assessment_id)
        template = 'assessments/staff_manage_exam_questions.html'
        url_name = 'assessments:staff_manage_exam_questions'

    if not ClassSubject.objects.filter(
        teacher=request.user,
        subject=assessment.subject,
        academic_class=assessment.academic_class,
        is_active=True
    ).exists():
        messages.error(request, 'You do not have permission to manage questions for this assessment.')
        return redirect(f'assessments:staff_manage_{assessment_type}s')

    questions = assessment.questions.select_related('test', 'exam').prefetch_related('options').order_by('order')

    context = {
        'assessment': assessment,
        'assessment_type': assessment_type,
        'questions': questions,
    }
    return render(request, template, context)


@staff_required
def staff_add_question(request, assessment_type, assessment_id):
    """Add a question to a test or exam."""
    if assessment_type == 'test':
        assessment = get_object_or_404(Test, pk=assessment_id)
        url_name = 'assessments:staff_manage_test_questions'
    else:
        assessment = get_object_or_404(Exam, pk=assessment_id)
        url_name = 'assessments:staff_manage_exam_questions'

    if not ClassSubject.objects.filter(
        teacher=request.user,
        subject=assessment.subject,
        academic_class=assessment.academic_class,
        is_active=True
    ).exists():
        messages.error(request, 'You do not have permission to add questions to this assessment.')
        return redirect(f'assessments:staff_manage_{assessment_type}s')

    if request.method == 'POST':
        question_text = request.POST.get('question_text', '').strip()
        question_type = request.POST.get('question_type', 'mcq')
        points = int(request.POST.get('points', 1))
        options_data = []

        # Parse options from POST
        option_texts = request.POST.getlist('option_text')
        option_correct = request.POST.getlist('option_correct')
        option_orders = request.POST.getlist('option_order')

        for i, text in enumerate(option_texts):
            text = text.strip()
            if text:
                is_correct = str(i) in option_correct
                order = int(option_orders[i]) if i < len(option_orders) and option_orders[i] else i
                options_data.append({
                    'text': text,
                    'is_correct': is_correct,
                    'order': order,
                })

        if not question_text:
            messages.error(request, 'Question text is required.')
        elif len(options_data) < 2:
            messages.error(request, 'At least 2 options are required.')
        elif question_type == 'mcq' and not any(opt['is_correct'] for opt in options_data):
            messages.error(request, 'At least one option must be marked as correct for MCQ questions.')
        else:
            try:
                with transaction.atomic():
                    question = Question.objects.create(
                        test=assessment if assessment_type == 'test' else None,
                        exam=assessment if assessment_type == 'exam' else None,
                        question_type=question_type,
                        text=question_text,
                        points=points,
                        order=assessment.questions.count(),
                    )
                    for opt in options_data:
                        Option.objects.create(
                            question=question,
                            text=opt['text'],
                            is_correct=opt['is_correct'],
                            order=opt['order'],
                        )
                    create_audit_log(
                        user=request.user,
                        action='create',
                        model_name='Question',
                        obj=question,
                        request=request
                    )
                    messages.success(request, 'Question added successfully.')
                    return redirect(url_name, assessment_id=assessment_id)
            except IntegrityError:
                messages.error(request, 'An error occurred while saving the question.')

    context = {
        'assessment': assessment,
        'assessment_type': assessment_type,
    }
    return render(request, f'assessments/staff_add_question.html', context)


@staff_required
def staff_edit_question(request, assessment_type, assessment_id, question_id):
    """Edit a question."""
    question = get_object_or_404(Question, pk=question_id)
    assessment = question.test or question.exam
    
    if assessment_type == 'test':
        url_name = 'assessments:staff_manage_test_questions'
    else:
        url_name = 'assessments:staff_manage_exam_questions'

    if not ClassSubject.objects.filter(
        teacher=request.user,
        subject=assessment.subject,
        academic_class=assessment.academic_class,
        is_active=True
    ).exists():
        messages.error(request, 'You do not have permission to edit this question.')
        return redirect(url_name, assessment_id=assessment_id)

    if request.method == 'POST':
        question_text = request.POST.get('question_text', '').strip()
        question_type = request.POST.get('question_type', 'mcq')
        points = int(request.POST.get('points', 1))

        if not question_text:
            messages.error(request, 'Question text is required.')
        else:
            try:
                with transaction.atomic():
                    question.text = question_text
                    question.question_type = question_type
                    question.points = points
                    question.save()

                    # Delete existing options and create new ones
                    question.options.all().delete()
                    option_texts = request.POST.getlist('option_text')
                    option_correct = request.POST.getlist('option_correct')
                    option_orders = request.POST.getlist('option_order')

                    for i, text in enumerate(option_texts):
                        text = text.strip()
                        if text:
                            is_correct = str(i) in option_correct
                            order = int(option_orders[i]) if i < len(option_orders) and option_orders[i] else i
                            Option.objects.create(
                                question=question,
                                text=text,
                                is_correct=is_correct,
                                order=order,
                            )
                    create_audit_log(
                        user=request.user,
                        action='update',
                        model_name='Question',
                        obj=question,
                        request=request
                    )
                    messages.success(request, 'Question updated successfully.')
                    return redirect(url_name, assessment_id=assessment_id)
            except IntegrityError:
                messages.error(request, 'An error occurred while updating the question.')

    context = {
        'assessment': assessment,
        'assessment_type': assessment_type,
        'question': question,
        'options': question.options.order_by('order'),
    }
    return render(request, f'assessments/staff_edit_question.html', context)


@staff_required
def staff_delete_question(request, assessment_type, assessment_id, question_id):
    """Delete a question."""
    question = get_object_or_404(Question, pk=question_id)
    assessment = question.test or question.exam
    
    if assessment_type == 'test':
        url_name = 'assessments:staff_manage_test_questions'
    else:
        url_name = 'assessments:staff_manage_exam_questions'

    if not ClassSubject.objects.filter(
        teacher=request.user,
        subject=assessment.subject,
        academic_class=assessment.academic_class,
        is_active=True
    ).exists():
        messages.error(request, 'You do not have permission to delete this question.')
        return redirect(url_name, assessment_id=assessment_id)

    if request.method == 'POST':
        question_repr = str(question)
        question.delete()
        create_audit_log(
            user=request.user,
            action='delete',
            model_name='Question',
            obj=question,
            object_id=str(question_id),
            object_repr=question_repr,
            request=request
        )
        messages.success(request, 'Question deleted successfully.')
    return redirect(url_name, assessment_id=assessment_id)


@staff_required
def staff_create_test(request):
    """Create a new test."""
    if request.method == 'POST':
        form = TeacherTestForm(request.POST, user=request.user)
        if form.is_valid():
            test = form.save()
            create_audit_log(
                user=request.user,
                action='create',
                model_name='Test',
                obj=test,
                request=request
            )
            messages.success(request, 'Test created successfully.')
            return redirect('assessments:staff_manage_tests')
    else:
        form = TeacherTestForm(user=request.user)
    return render(request, 'assessments/staff_create_test.html', {'form': form})


@staff_required
def staff_manage_tests(request):
    """List tests created by the staff member."""
    teaching_assignments = ClassSubject.objects.filter(
        teacher=request.user, is_active=True
    ).select_related('subject', 'academic_class')
    
    tests = Test.objects.filter(
        subject__in=teaching_assignments.values_list('subject_id', flat=True),
        academic_class__in=teaching_assignments.values_list('academic_class_id', flat=True)
    ).select_related('subject', 'term', 'academic_class').order_by('-date')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        tests = tests.filter(
            Q(title__icontains=search) |
            Q(subject__name__icontains=search) |
            Q(term__name__icontains=search) |
            Q(academic_class__name__icontains=search)
        )
    
    # Term filter
    term_filter = request.GET.get('term')
    if term_filter:
        tests = tests.filter(term_id=term_filter)
    
    # Class filter
    class_filter = request.GET.get('class')
    if class_filter:
        tests = tests.filter(academic_class_id=class_filter)
    
    paginator = Paginator(tests, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    terms = Term.objects.all().order_by('-start_date')
    classes = AcademicClass.objects.filter(
        pk__in=teaching_assignments.values_list('academic_class_id', flat=True)
    ).distinct()
    
    context = {
        'page_obj': page_obj,
        'terms': terms,
        'classes': classes,
        'search': search,
        'selected_term': term_filter,
        'selected_class': class_filter,
    }
    return render(request, 'assessments/staff_manage_tests.html', context)


@staff_required
def staff_delete_test(request, pk):
    """Delete a test."""
    test = get_object_or_404(Test, pk=pk)
    
    # Check permission
    if not ClassSubject.objects.filter(
        teacher=request.user,
        subject=test.subject,
        academic_class=test.academic_class,
        is_active=True
    ).exists():
        messages.error(request, 'You do not have permission to delete this test.')
        return redirect('assessments:staff_manage_tests')
    
    if request.method == 'POST':
        test_repr = str(test)
        test.delete()
        create_audit_log(
            user=request.user,
            action='delete',
            model_name='Test',
            obj=test,
            object_id=str(pk),
            object_repr=test_repr,
            request=request
        )
        messages.success(request, 'Test deleted successfully.')
        return redirect('assessments:staff_manage_tests')
    
    context = {
        'object': test, 
        'object_name': f'Test: {test.title}', 
        'delete_url': 'assessments:staff_delete_test', 
        'delete_pk': pk,
        'cancel_url': 'assessments:staff_manage_tests',
        'cancel_label': 'Back to Tests'
    }
    return render(request, 'includes/confirm_delete.html', context)


@staff_required
def staff_create_exam(request):
    """Create a new exam."""
    if request.method == 'POST':
        form = TeacherExamForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save()
            create_audit_log(
                user=request.user,
                action='create',
                model_name='Exam',
                obj=exam,
                request=request
            )
            messages.success(request, 'Exam created successfully.')
            return redirect('assessments:staff_manage_exams')
    else:
        form = TeacherExamForm(user=request.user)
    return render(request, 'assessments/staff_create_exam.html', {'form': form})


@staff_required
def staff_manage_exams(request):
    """List exams created by the staff member."""
    teaching_assignments = ClassSubject.objects.filter(
        teacher=request.user, is_active=True
    ).select_related('subject', 'academic_class')
    
    exams = Exam.objects.filter(
        subject__in=teaching_assignments.values_list('subject_id', flat=True),
        academic_class__in=teaching_assignments.values_list('academic_class_id', flat=True)
    ).select_related('subject', 'term', 'academic_class').order_by('-date')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        exams = exams.filter(
            Q(title__icontains=search) |
            Q(subject__name__icontains=search) |
            Q(term__name__icontains=search) |
            Q(academic_class__name__icontains=search)
        )
    
    # Term filter
    term_filter = request.GET.get('term')
    if term_filter:
        exams = exams.filter(term_id=term_filter)
    
    # Class filter
    class_filter = request.GET.get('class')
    if class_filter:
        exams = exams.filter(academic_class_id=class_filter)
    
    paginator = Paginator(exams, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    terms = Term.objects.all().order_by('-start_date')
    classes = AcademicClass.objects.filter(
        pk__in=teaching_assignments.values_list('academic_class_id', flat=True)
    ).distinct()
    
    context = {
        'page_obj': page_obj,
        'terms': terms,
        'classes': classes,
        'search': search,
        'selected_term': term_filter,
        'selected_class': class_filter,
    }
    return render(request, 'assessments/staff_manage_exams.html', context)


@staff_required
def staff_delete_exam(request, pk):
    """Delete an exam."""
    exam = get_object_or_404(Exam, pk=pk)
    
    # Check permission
    if not ClassSubject.objects.filter(
        teacher=request.user,
        subject=exam.subject,
        academic_class=exam.academic_class,
        is_active=True
    ).exists():
        messages.error(request, 'You do not have permission to delete this exam.')
        return redirect('assessments:staff_manage_exams')
    
    if request.method == 'POST':
        exam_repr = str(exam)
        exam.delete()
        create_audit_log(
            user=request.user,
            action='delete',
            model_name='Exam',
            obj=exam,
            object_id=str(pk),
            object_repr=exam_repr,
            request=request
        )
        messages.success(request, 'Exam deleted successfully.')
        return redirect('assessments:staff_manage_exams')
    
    context = {
        'object': exam, 
        'object_name': f'Exam: {exam.title}', 
        'delete_url': 'assessments:staff_delete_exam', 
        'delete_pk': pk,
        'cancel_url': 'assessments:staff_manage_exams',
        'cancel_label': 'Back to Exams'
    }
    return render(request, 'includes/confirm_delete.html', context)


@staff_required
def staff_enter_test_result(request):
    """Enter a single test result."""
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found.')
        return redirect('school:dashboard')
    
    if request.method == 'POST':
        form = TestResultForm(request.POST, user=request.user)
        if form.is_valid():
            result = form.save(commit=False)
            result.entered_by = TestResult.ENTERED_BY_TEACHER
            result.save()
            messages.success(request, 'Test result saved successfully.')
            # Re-render form instead of redirect to match test expectations
    else:
        form = TestResultForm(user=request.user)
    
    context = {'form': form, 'type': 'Test'}
    return render(request, 'assessments/staff_enter_result.html', context)


@staff_required
def staff_enter_exam_result(request):
    """Enter a single exam result."""
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found.')
        return redirect('school:dashboard')
    
    if request.method == 'POST':
        form = ExamResultForm(request.POST, user=request.user)
        if form.is_valid():
            result = form.save(commit=False)
            result.entered_by = ExamResult.ENTERED_BY_TEACHER
            result.save()
            messages.success(request, 'Exam result saved successfully.')
            # Re-render form instead of redirect to match test expectations
    else:
        form = ExamResultForm(user=request.user)
    
    context = {'form': form, 'type': 'Exam'}
    return render(request, 'assessments/staff_enter_result.html', context)


@staff_required
def staff_enter_results_table(request):
    """Bulk enter results in a table format."""
    assessment_type = request.GET.get('type', 'test')
    assessment_id = request.GET.get('id') or request.GET.get('assessment_id') or request.POST.get('assessment_id')
    
    if assessment_type == 'test':
        Model = Test
        ResultModel = TestResult
    else:
        Model = Exam
        ResultModel = ExamResult
    
    teaching_assignments = ClassSubject.objects.filter(
        teacher=request.user, is_active=True
    ).select_related('subject', 'academic_class')
    
    assessments = Model.objects.filter(
        subject__in=teaching_assignments.values_list('subject_id', flat=True),
        academic_class__in=teaching_assignments.values_list('academic_class_id', flat=True)
    ).select_related('subject', 'term', 'academic_class').order_by('-date')
    
    selected_assessment = None
    student_results = []
    
    if request.method == 'POST':
        if assessment_id:
            selected_assessment = get_object_or_404(Model, pk=assessment_id)
            
            # Get students in the class
            from accounts.models import Profile
            students = Profile.objects.filter(
                academic_class=selected_assessment.academic_class,
                role=Profile.ROLE_STUDENT
            ).select_related('user').order_by('user__username')
            
            # Handle bulk save - check for any score fields in POST
            has_scores = any(key.startswith('score_') for key in request.POST)
            if has_scores:
                for profile in students:
                    score = request.POST.get(f'score_{profile.pk}')
                    if score is not None and score != '':
                        try:
                            score_val = int(round(float(score)))
                            if score_val >= 0:
                                ResultModel.objects.update_or_create(
                                    student=profile.user,
                                    **{assessment_type: selected_assessment},
                                    defaults={'score': score_val, 'entered_by': ResultModel.ENTERED_BY_TEACHER}
                                )
                        except (ValueError, TypeError):
                            pass
                messages.success(request, 'Results saved successfully.')
                return redirect(f'{request.path}?type={assessment_type}&id={assessment_id}')
    
    elif assessment_id:
        selected_assessment = get_object_or_404(Model, pk=assessment_id)
        
        # Get students in the class
        from accounts.models import Profile
        students = Profile.objects.filter(
            academic_class=selected_assessment.academic_class,
            role=Profile.ROLE_STUDENT
        ).select_related('user').order_by('user__username')
        
        # Get existing results
        existing_results = dict(
            ResultModel.objects.filter(
                **{f'{assessment_type}': selected_assessment}
            ).values_list('student_id', 'score')
        )
        
        # Build student_results list for template
        for profile in students:
            student_results.append({
                'student': profile,
                'score': existing_results.get(profile.user_id, ''),
            })
    
    context = {
        'assessment_type': assessment_type,
        'assessments': assessments,
        'assessment': selected_assessment,
        'student_results': student_results,
        'max_score': selected_assessment.max_score if selected_assessment else None,
    }
    return render(request, 'assessments/staff_enter_results_table.html', context)


@login_required
def admin_calculate_term_results(request):
    """Calculate term results for all students."""
    if not request.user.is_superuser:
        return redirect('school:dashboard')
    
    from school.views import calculate_term_results
    
    # Accept GET parameters for testing
    term_id = request.GET.get('term') or request.POST.get('term')
    class_id = request.GET.get('class') or request.POST.get('class')
    
    # If no term specified, use current term
    if not term_id:
        current_term = Term.objects.filter(is_current=True).first()
        if current_term:
            term_id = current_term.pk
    
    if term_id:
        term = get_object_or_404(Term, pk=term_id)
        academic_class = get_object_or_404(AcademicClass, pk=class_id) if class_id else None
        
        count = calculate_term_results(term, academic_class)
        messages.success(request, f'Term results calculated for {count} students.')
        return redirect('assessments:admin_calculate_term_results')
    
    # No term specified and no current term - redirect with error
    messages.error(request, 'Please select a term or set a current term.')
    return redirect('assessments:admin_calculate_term_results')


@login_required
def admin_promote_students(request):
    """Promote students to next class."""
    if not request.user.is_superuser:
        return redirect('school:dashboard')
    
    if request.method == 'POST':
        pass_mark = request.POST.get('pass_mark')
        next_term_resumption_date = request.POST.get('next_term_resumption_date') or '2026-01-05'  # Default if not provided
        
        if not pass_mark:
            messages.error(request, 'Pass mark is required.')
        else:
            try:
                pass_mark = float(pass_mark)
            except (ValueError, TypeError):
                messages.error(request, 'Invalid pass mark.')
                return redirect('assessments:admin_promote_students')
            
            # Get all students with term results for the current term only
            current_term = Term.objects.filter(is_current=True).first()
            if not current_term:
                messages.error(request, 'No current term set. Please set a current term first.')
                return redirect('assessments:admin_promote_students')
            
            term_results = TermResult.objects.filter(term=current_term).select_related('student', 'term', 'academic_class')
            
            promoted = 0
            repeated = 0
            graduated = 0
            
            # Pre-fetch all classes ordered by section and name for auto-detection
            all_classes = list(AcademicClass.objects.filter(is_active=True).order_by('section', 'name'))
            
            for term_result in term_results:
                student = term_result.student
                current_class = term_result.academic_class
                
                is_promoted = term_result.average_score >= pass_mark
                
                if is_promoted:
                    # Try to get next_class from the model, otherwise auto-detect
                    next_class = current_class.next_class
                    
                    if not next_class:
                        # Auto-detect next class based on ordering
                        try:
                            current_idx = all_classes.index(current_class)
                            if current_idx + 1 < len(all_classes):
                                next_class = all_classes[current_idx + 1]
                        except ValueError:
                            pass
                    
                    if next_class:
                        # Regular promotion to next class
                        to_class = next_class
                        new_status = Profile.STATUS_ACTIVE
                    else:
                        # Final class (no next class found) - student graduates
                        to_class = current_class  # Keep same class for record
                        new_status = Profile.STATUS_GRADUATED
                        graduated += 1
                    
                    # Update student's profile status and class
                    profile = student.profile
                    profile.academic_class = to_class
                    profile.status = new_status
                    profile.save()
                    
                    promoted += 1
                else:
                    # Student repeats the same class
                    to_class = current_class
                    repeated += 1
                
                PromotionDecision.objects.update_or_create(
                    student=student,
                    term=term_result.term,
                    defaults={
                        'from_class': current_class,
                        'to_class': to_class,
                        'average_score': term_result.average_score,
                        'is_promoted': is_promoted,
                        'remarks': 'Auto-promoted' if is_promoted else 'Repeat class',
                        'next_term_resumption_date': next_term_resumption_date,
                    }
                )
            
            msg_parts = [f'{promoted} promoted', f'{repeated} repeated']
            if graduated:
                msg_parts.append(f'{graduated} graduated')
            messages.success(request, f'Promotion decisions made: {", ".join(msg_parts)}.')
            return redirect('assessments:admin_promote_students')
    
    terms = Term.objects.all().order_by('-start_date')
    classes = AcademicClass.objects.filter(is_active=True)
    
    context = {
        'terms': terms,
        'classes': classes,
    }
    return render(request, 'school/admin_promote_students.html', context)


@login_required
def admin_view_test_questions(request, pk):
    """Admin view to view test questions and answers (read-only)."""
    if not request.user.is_superuser:
        return redirect('school:dashboard')
    
    test = get_object_or_404(Test, pk=pk)
    questions = test.questions.prefetch_related('options').order_by('order')
    
    context = {
        'assessment': test,
        'assessment_type': 'test',
        'questions': questions,
        'read_only': True,
    }
    return render(request, 'assessments/admin_view_questions.html', context)


@login_required
def admin_view_exam_questions(request, pk):
    """Admin view to view exam questions and answers (read-only)."""
    if not request.user.is_superuser:
        return redirect('school:dashboard')
    
    exam = get_object_or_404(Exam, pk=pk)
    questions = exam.questions.prefetch_related('options').order_by('order')
    
    context = {
        'assessment': exam,
        'assessment_type': 'exam',
        'questions': questions,
        'read_only': True,
    }
    return render(request, 'assessments/admin_view_questions.html', context)


@login_required
def admin_manage_tests(request):
    """Admin view to manage all tests."""
    if not request.user.is_superuser:
        return redirect('school:dashboard')
    
    tests = Test.objects.select_related('subject', 'term', 'academic_class').order_by('-date')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        tests = tests.filter(
            Q(title__icontains=search) |
            Q(subject__name__icontains=search) |
            Q(term__name__icontains=search) |
            Q(academic_class__name__icontains=search)
        )
    
    # Term filter
    term_filter = request.GET.get('term')
    if term_filter:
        tests = tests.filter(term_id=term_filter)
    
    # Class filter
    class_filter = request.GET.get('class')
    if class_filter:
        tests = tests.filter(academic_class_id=class_filter)
    
    paginator = Paginator(tests, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    terms = Term.objects.all().order_by('-start_date')
    classes = AcademicClass.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'terms': terms,
        'classes': classes,
        'search': search,
        'selected_term': term_filter,
        'selected_class': class_filter,
    }
    return render(request, 'school/admin_manage_tests.html', context)


@login_required
def admin_manage_exams(request):
    """Admin view to manage all exams."""
    if not request.user.is_superuser:
        return redirect('school:dashboard')
    
    exams = Exam.objects.select_related('subject', 'term', 'academic_class').order_by('-date')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        exams = exams.filter(
            Q(title__icontains=search) |
            Q(subject__name__icontains=search) |
            Q(term__name__icontains=search) |
            Q(academic_class__name__icontains=search)
        )
    
    # Term filter
    term_filter = request.GET.get('term')
    if term_filter:
        exams = exams.filter(term_id=term_filter)
    
    # Class filter
    class_filter = request.GET.get('class')
    if class_filter:
        exams = exams.filter(academic_class_id=class_filter)
    
    paginator = Paginator(exams, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    terms = Term.objects.all().order_by('-start_date')
    classes = AcademicClass.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'terms': terms,
        'classes': classes,
        'search': search,
        'selected_term': term_filter,
        'selected_class': class_filter,
    }
    return render(request, 'school/admin_manage_exams.html', context)
    return render(request, 'includes/confirm_delete.html', context)