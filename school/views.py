from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import IntegrityError
from django.db import transaction
from django.core.paginator import Paginator
from django.http import HttpResponse
import csv
import random
import string

from .models import (
    Term, AcademicClass, Subject, ClassSubject, ClassTeacher,
    Test, Exam, TestResult, ExamResult,
    TermResult, PromotionDecision, GradeBoundary, ResultRemark, ReportCard,
    ParentProfile, SchoolEvent, Fee, Payment, AuditLog
)
from accounts.models import Profile
from .forms import (
    AdminCreateStudentForm, AdminCreateParentForm, GradeBoundaryForm, ResultRemarkForm,
    ParentProfileForm, SchoolEventForm, FeeForm, PaymentForm
)
from .utils import (
    create_audit_log, get_user_profile, get_grade_boundaries, annotate_results,
    get_client_ip, safe_float, safe_int
)


def home(request):
    current_term = Term.objects.filter(is_current=True).first()
    classes = AcademicClass.objects.filter(is_active=True)
    context = {
        'current_term': current_term,
        'classes': classes,
    }
    return render(request, 'home.html', context)


def login_view(request):
    from django.contrib.auth import authenticate, login
    from django.contrib.auth.forms import AuthenticationForm

    if request.user.is_authenticated:
        return redirect('school:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('school:dashboard')
    else:
        form = AuthenticationForm()
        for field_name, field in form.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label
            })

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def dashboard(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:home')
    if profile.role == Profile.ROLE_STAFF:
        return redirect('staff:staff_dashboard')
    elif request.user.is_superuser:
        return redirect('school:admin_dashboard')
    elif profile.role == Profile.ROLE_PARENT:
        return redirect('school:parent_dashboard')
    return redirect('students:student_dashboard')


@login_required
def student_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role != Profile.ROLE_STAFF and not request.user.is_superuser:
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
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    total_students = Profile.objects.filter(role=Profile.ROLE_STUDENT).count()
    total_staff = Profile.objects.filter(role=Profile.ROLE_STAFF).count()
    total_classes = AcademicClass.objects.filter(is_active=True).count()
    current_term = Term.objects.filter(is_current=True).first()

    recent_students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT
    ).select_related('user', 'academic_class').order_by('-created_at')[:10]

    context = {
        'total_students': total_students,
        'total_staff': total_staff,
        'total_classes': total_classes,
        'current_term': current_term,
        'recent_students': recent_students,
    }
    return render(request, 'school/admin_dashboard.html', context)


@login_required
def student_subjects(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    current_term = Term.objects.filter(is_current=True).first()
    academic_class = profile.academic_class

    class_subjects = []
    if academic_class:
        class_subjects = ClassSubject.objects.filter(
            academic_class=academic_class, is_active=True
        ).select_related('subject', 'teacher')

    context = {
        'current_term': current_term,
        'academic_class': academic_class,
        'class_subjects': class_subjects,
    }
    return render(request, 'student_subjects.html', context)


@login_required
def take_test(request, test_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    test = get_object_or_404(Test, pk=test_id, is_active=True)

    if request.method == 'POST':
        score = request.POST.get('score')
        try:
            score = float(score)
            score_int = int(round(score))
            if score_int < 0 or score_int > test.max_score:
                messages.error(request, f'Score must be between 0 and {test.max_score}.')
            else:
                result, created = TestResult.objects.update_or_create(
                    student=request.user,
                    test=test,
                    defaults={'score': score_int, 'entered_by': TestResult.ENTERED_BY_STUDENT}
                )
                messages.success(request, 'Test submitted successfully.')
                return redirect('my_results')
        except ValueError:
            messages.error(request, 'Invalid score.')

    context = {
        'test': test,
    }
    return render(request, 'take_test.html', context)


@login_required
def take_exam(request, exam_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    exam = get_object_or_404(Exam, pk=exam_id, is_active=True)

    if request.method == 'POST':
        score = request.POST.get('score')
        try:
            score = float(score)
            score_int = int(round(score))
            if score_int < 0 or score_int > exam.max_score:
                messages.error(request, f'Score must be between 0 and {exam.max_score}.')
            else:
                result, created = ExamResult.objects.update_or_create(
                    student=request.user,
                    exam=exam,
                    defaults={'score': score_int, 'entered_by': ExamResult.ENTERED_BY_STUDENT}
                )
                messages.success(request, 'Exam submitted successfully.')
                return redirect('my_results')
        except ValueError:
            messages.error(request, 'Invalid score.')

    context = {
        'exam': exam,
    }
    return render(request, 'take_exam.html', context)


@login_required
def my_results(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
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
    return render(request, 'my_results.html', context)


@login_required
def term_results(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    term_results = TermResult.objects.filter(
        student=request.user
    ).select_related('term', 'academic_class').order_by('-term')

    promotion_decisions = PromotionDecision.objects.filter(
        student=request.user
    ).select_related('term', 'from_class', 'to_class').order_by('-term')

    context = {
        'term_results': term_results,
        'promotion_decisions': promotion_decisions,
    }
    return render(request, 'term_results.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_create_student(request):
    activation_token = request.session.pop('student_activation_token', None)
    activation_matric = request.session.pop('student_activation_admission', None)
    
    if request.method == 'POST':
        form = AdminCreateStudentForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            academic_class = form.cleaned_data.get('academic_class')
            phone = form.cleaned_data.get('phone', '')
            gender = form.cleaned_data.get('gender', '')

            base_username = f"{first_name}.{last_name}".lower().replace(' ', '.')
            if not base_username or base_username == '.':
                base_username = f"student{Profile.objects.filter(role=Profile.ROLE_STUDENT).count() + 1}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        password=None,
                        first_name=first_name,
                        last_name=last_name,
                    )
                    user.set_unusable_password()
                    user.save()

                    profile, _ = Profile.objects.get_or_create(user=user, defaults={
                        'role': Profile.ROLE_STUDENT,
                    })
                    profile.academic_class = academic_class
                    profile.phone = phone
                    profile.gender = gender
                    token = str(random.randint(10000, 99999))
                    while Profile.objects.filter(activation_token=token).exists():
                        token = str(random.randint(10000, 99999))
                    profile.activation_token = token
                    profile.is_activated = False
                    profile.save()

                    messages.success(request, f'Student created. Admission Number: {profile.admission_number}. Share the 5-digit token with the student.')
                    request.session['student_activation_token'] = profile.activation_token
                    request.session['student_activation_admission'] = profile.admission_number
                    return redirect('school:admin_create_student')
            except IntegrityError:
                messages.error(request, 'An error occurred while creating the student. Please try again.')
    else:
        form = AdminCreateStudentForm()

    return render(request, 'school/admin_create_student.html', {
        'form': form,
        'activation_token': activation_token,
        'activation_matric': activation_matric,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_create_parent(request):
    """Handle parent account creation with optional student linking.

    Creates a new parent User with unusable password, generates an invitation
    code, sets up their Profile with ROLE_PARENT, and optionally creates a
    ParentProfile link to a selected student.

    GET: Display form to create parent (optionally filtered by class).
    POST: Process form, create parent user and profile, optionally link student.
    """
    class_id = request.GET.get('class_id') or request.POST.get('class_id')
    student_id = request.GET.get('student_id') or request.POST.get('student_id')
    selected_student = None

    if request.method == 'POST':
        form = AdminCreateParentForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data.get('email', '')
            phone = form.cleaned_data.get('phone', '')
            student = form.cleaned_data.get('student')
            if not student and student_id:
                try:
                    student = User.objects.get(pk=student_id)
                except User.DoesNotExist:
                    student = None
            relationship = form.cleaned_data.get('relationship', 'guardian')
            is_primary = form.cleaned_data.get('is_primary', False)

            base_username = f"{first_name}.{last_name}".lower().replace(' ', '.')
            if not base_username or base_username == '.':
                base_username = f"parent{User.objects.count() + 1}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=username,
                        password=None,
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                    )
                    user.set_unusable_password()
                    user.save()

                    unique_id = 'PAR-' + ''.join(random.choices(string.digits, k=6))
                    while Profile.objects.filter(unique_id=unique_id).exists():
                        unique_id = 'PAR-' + ''.join(random.choices(string.digits, k=6))

                    profile, _ = Profile.objects.get_or_create(
                        user=user,
                        defaults={'role': Profile.ROLE_PARENT}
                    )
                    profile.role = Profile.ROLE_PARENT
                    profile.unique_id = unique_id
                    profile.is_activated = True
                    profile.phone = phone
                    profile.save()

                    create_audit_log(
                        user=request.user,
                        action='create',
                        model_name='User',
                        obj=user,
                        changes={'role': Profile.ROLE_PARENT, 'unique_id': unique_id},
                        request=request
                    )

                    if student:
                        parent_link = ParentProfile.objects.create(
                            parent=user,
                            student=student,
                            relationship=relationship,
                            phone=phone,
                            email=email,
                            is_primary=is_primary,
                        )
                        create_audit_log(
                            user=request.user,
                            action='create',
                            model_name='ParentProfile',
                            obj=parent_link,
                            request=request
                        )

                    messages.success(request, f'Parent created. Invitation code: {unique_id}. Username: {username}')
                    return redirect('school:admin_parent_profiles')
            except IntegrityError:
                messages.error(request, 'An error occurred while creating the parent. Please try again.')
    else:
        form = AdminCreateParentForm()

    if class_id:
        form.fields['student'].queryset = User.objects.filter(
            profile__role=Profile.ROLE_STUDENT,
            profile__status=Profile.STATUS_ACTIVE,
            profile__academic_class_id=class_id
        ).select_related('profile', 'profile__academic_class')

    if student_id and class_id:
        try:
            selected_student = User.objects.get(
                pk=student_id,
                profile__role=Profile.ROLE_STUDENT,
                profile__status=Profile.STATUS_ACTIVE,
                profile__academic_class_id=class_id
            )
            form.fields['student'].initial = selected_student
            form.fields['student'].widget.attrs['disabled'] = True
        except User.DoesNotExist:
            selected_student = None

    classes = AcademicClass.objects.filter(is_active=True).order_by('name')
    return render(request, 'school/admin_create_parent.html', {
        'form': form,
        'classes': classes,
        'selected_class_id': class_id,
        'selected_student': selected_student,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_students(request):
    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT
    ).select_related('user', 'academic_class').order_by('academic_class__name', 'user__username')

    class_teachers = ClassTeacher.objects.filter(is_active=True).select_related('academic_class', 'teacher')
    class_teacher_map = {ct.academic_class_id: ct.teacher for ct in class_teachers}

    classes = AcademicClass.objects.filter(is_active=True).order_by('name')
    students_by_class = {}
    for cls in classes:
        students_by_class[cls] = [s for s in students if s.academic_class_id == cls.pk]

    unassigned_students = [s for s in students if s.academic_class_id is None]

    class_student_list = [(cls, students_by_class[cls], class_teacher_map.get(cls.pk)) for cls in classes if students_by_class[cls]]

    return render(request, 'admin_students.html', {
        'class_student_list': class_student_list,
        'classes': classes,
        'unassigned_students': unassigned_students,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_class(request, pk):
    cls = get_object_or_404(AcademicClass, pk=pk)
    if request.method == 'POST':
        try:
            cls.delete()
            messages.success(request, 'Class deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this class because it has related records. Remove them first.')
    return redirect('school:admin_classes')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_student(request, pk):
    profile = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_STUDENT)
    if request.method == 'POST':
        try:
            user = profile.user
            profile.delete()
            user.delete()
            messages.success(request, 'Student removed successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this student because they have related assessment records. Remove them first.')
    return redirect('school:admin_students')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_all_results(request):
    """Display paginated class-wise results for all students."""
    current_term = Term.objects.filter(is_current=True).first()
    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT,
        academic_class__isnull=False
    ).select_related('user', 'academic_class')

    search = request.GET.get('q', '').strip()
    if search:
        students = students.filter(
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(admission_number__icontains=search)
        )

    class_filter = request.GET.get('class_id', '').strip()
    if class_filter:
        students = students.filter(academic_class_id=class_filter)

    students = students.order_by('academic_class__name', 'user__username')

    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    class_results = {}
    for student in page_obj:
        cls = student.academic_class
        if cls not in class_results:
            class_results[cls] = []
        term_results = TermResult.objects.filter(
            student=student.user,
            academic_class=cls
        ).select_related('term').order_by('-term')
        test_count = TestResult.objects.filter(student=student.user).count()
        exam_count = ExamResult.objects.filter(student=student.user).count()
        class_results[cls].append({
            'student': student,
            'term_results': term_results,
            'test_count': test_count,
            'exam_count': exam_count,
        })

    classes = AcademicClass.objects.filter(is_active=True).order_by('name')

    context = {
        'current_term': current_term,
        'class_results': [
            {
                'class': cls,
                'students': students,
            }
            for cls, students in class_results.items()
        ],
        'page_obj': page_obj,
        'search': search,
        'class_filter': class_filter,
        'classes': classes,
    }
    return render(request, 'school/admin_all_results.html', context)


@login_required
def parent_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role != Profile.ROLE_PARENT:
        messages.error(request, 'Access denied. Parent accounts only.')
        return redirect('school:dashboard')
    
    parent_links = ParentProfile.objects.filter(
        parent=request.user
    ).select_related('student', 'student__profile', 'student__profile__academic_class').order_by('student__username')
    
    children = []
    for link in parent_links:
        student = link.student
        student_profile = student.profile
        academic_class = student_profile.academic_class
        
        current_term = Term.objects.filter(is_current=True).first()
        term_results = []
        if current_term:
            term_results = TermResult.objects.filter(
                student=student,
                term=current_term,
                academic_class=academic_class
            ).select_related('term', 'academic_class').order_by('-term') if academic_class else []
        
        test_count = TestResult.objects.filter(student=student).count()
        exam_count = ExamResult.objects.filter(student=student).count()
        
        recent_results = TestResult.objects.filter(
            student=student
        ).select_related('test', 'test__subject', 'test__term').order_by('-submitted_at')[:5]
        
        report_cards = ReportCard.objects.filter(
            student=student
        ).select_related('term', 'academic_class').order_by('-generated_at')[:3]
        
        children.append({
            'student': student,
            'profile': student_profile,
            'status': student_profile.get_status_display(),
            'academic_class': academic_class,
            'relationship': link.get_relationship_display(),
            'term_results': term_results,
            'test_count': test_count,
            'exam_count': exam_count,
            'recent_results': recent_results,
            'report_cards': report_cards,
        })
    
    context = {
        'children': children,
    }
    return render(request, 'school/parent_dashboard.html', context)


@login_required
def parent_child_detail(request, student_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role != Profile.ROLE_PARENT:
        messages.error(request, 'Access denied. Parent accounts only.')
        return redirect('school:dashboard')
    
    parent_link = get_object_or_404(ParentProfile, parent=request.user, student_id=student_id)
    student = parent_link.student
    student_profile = student.profile
    academic_class = student_profile.academic_class
    
    current_term = Term.objects.filter(is_current=True).first()
    
    test_results = TestResult.objects.filter(
        student=student
    ).select_related('test', 'test__subject', 'test__term', 'test__academic_class').order_by('-test__date')
    
    exam_results = ExamResult.objects.filter(
        student=student
    ).select_related('exam', 'exam__subject', 'exam__term', 'exam__academic_class').order_by('-exam__date')
    
    term_results = TermResult.objects.filter(
        student=student
    ).select_related('term', 'academic_class').order_by('-term')
    
    boundaries = GradeBoundary.objects.filter(is_active=True).order_by('-min_score')
    annotated_tests = annotate_results(test_results, 'score', boundaries)
    annotated_exams = annotate_results(exam_results, 'score', boundaries)
    annotated_term_results = annotate_results(term_results, 'average_score', boundaries)
    
    report_cards = ReportCard.objects.filter(
        student=student
    ).select_related('term', 'academic_class').order_by('-generated_at')
    
    context = {
        'student': student,
        'profile': student_profile,
        'status': student_profile.get_status_display(),
        'academic_class': academic_class,
        'relationship': parent_link.get_relationship_display(),
        'current_term': current_term,
        'test_results': annotated_tests,
        'exam_results': annotated_exams,
        'term_results': annotated_term_results,
        'report_cards': report_cards,
    }
    return render(request, 'school/parent_child_detail.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_grade_boundaries(request):
    boundaries = GradeBoundary.objects.all().order_by('-min_score')
    if request.method == 'POST':
        form = GradeBoundaryForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Grade boundary added successfully.')
                return redirect('school:admin_grade_boundaries')
            except IntegrityError:
                messages.error(request, 'An error occurred while saving the grade boundary. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = GradeBoundaryForm()
    return render(request, 'school/admin_grade_boundaries.html', {'boundaries': boundaries, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_grade_boundary(request, pk):
    boundary = get_object_or_404(GradeBoundary, pk=pk)
    if request.method == 'POST':
        try:
            boundary.delete()
            messages.success(request, 'Grade boundary deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this grade boundary because it has related records. Remove them first.')
    return redirect('school:admin_grade_boundaries')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_result_remarks(request):
    remarks = ResultRemark.objects.all().select_related('student', 'term', 'academic_class', 'created_by').order_by('-created_at')
    if request.method == 'POST':
        form = ResultRemarkForm(request.POST)
        if form.is_valid():
            try:
                remark = form.save(commit=False)
                remark.created_by = request.user
                remark.save()
                messages.success(request, 'Remark added successfully.')
                return redirect('school:admin_result_remarks')
            except IntegrityError:
                messages.error(request, 'An error occurred while adding the remark. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ResultRemarkForm()
    return render(request, 'school/admin_result_remarks.html', {'remarks': remarks, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_result_remark(request, pk):
    remark = get_object_or_404(ResultRemark, pk=pk)
    if request.method == 'POST':
        try:
            remark.delete()
            messages.success(request, 'Remark deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this remark because it has related records. Remove them first.')
    return redirect('school:admin_result_remarks')


@login_required
def report_card(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('school:dashboard')

    report_cards = ReportCard.objects.filter(
        student=request.user
    ).select_related('term', 'academic_class').order_by('-generated_at')

    boundaries = get_grade_boundaries()

    enriched_cards = []
    for card in report_cards:
        test_results = TestResult.objects.filter(
            student=request.user,
            test__term=card.term,
            test__academic_class=card.academic_class
        ).select_related('test', 'test__subject').order_by('test__subject__name')

        exam_results = ExamResult.objects.filter(
            student=request.user,
            exam__term=card.term,
            exam__academic_class=card.academic_class
        ).select_related('exam', 'exam__subject').order_by('exam__subject__name')

        subject_map = {}
        for tr in test_results:
            subj = tr.test.subject
            if subj not in subject_map:
                subject_map[subj] = {'test_score': None, 'test_max': None, 'exam_score': None, 'exam_max': None}
            subject_map[subj]['test_score'] = tr.score
            subject_map[subj]['test_max'] = tr.test.max_score
            subject_map[subj]['test_result'] = tr

        for er in exam_results:
            subj = er.exam.subject
            if subj not in subject_map:
                subject_map[subj] = {'test_score': None, 'test_max': None, 'exam_score': None, 'exam_max': None}
            subject_map[subj]['exam_score'] = er.score
            subject_map[subj]['exam_max'] = er.exam.max_score
            subject_map[subj]['exam_result'] = er

        subject_breakdown = []
        for subj in sorted(subject_map.keys(), key=lambda s: s.name):
            data = subject_map[subj]
            test_score = float(data['test_score']) if data.get('test_score') is not None else 0
            exam_score = float(data['exam_score']) if data.get('exam_score') is not None else 0
            test_max = float(data['test_max']) if data.get('test_max') is not None else 0
            exam_max = float(data['exam_max']) if data.get('exam_max') is not None else 0
            total_score = test_score + exam_score
            total_max = test_max + exam_max
            percentage = round((total_score / total_max) * 100, 2) if total_max > 0 else 0
            grade = None
            for boundary in boundaries:
                if boundary.min_score <= percentage <= boundary.max_score:
                    grade = boundary
                    break
            subject_breakdown.append({
                'subject': subj,
                'test_score': data.get('test_score'),
                'test_max': data.get('test_max'),
                'exam_score': data.get('exam_score'),
                'exam_max': data.get('exam_max'),
                'total_score': round(total_score, 2),
                'total_max': round(total_max, 2),
                'percentage': percentage,
                'grade': grade,
            })

        grade_boundary = None
        if card.average_score:
            for boundary in boundaries:
                if boundary.min_score <= float(card.average_score) <= boundary.max_score:
                    grade_boundary = boundary
                    break

        enriched_cards.append({
            'card': card,
            'subjects': subject_breakdown,
            'overall_grade': grade_boundary,
        })

    return render(request, 'students/report_card.html', {'report_cards': enriched_cards})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_generate_report_cards(request):
    current_term = Term.objects.filter(is_current=True).first()
    if not current_term:
        messages.error(request, 'No current term set.')
        return redirect('school:admin_dashboard')
    
    if request.method == 'POST':
        students = Profile.objects.filter(
            role=Profile.ROLE_STUDENT,
            academic_class__isnull=False
        ).select_related('user', 'academic_class')
        
        try:
            with transaction.atomic():
                for student in students:
                    academic_class = student.academic_class
                    term_results = TermResult.objects.filter(
                        student=student.user,
                        term=current_term,
                        academic_class=academic_class
                    ).first()
                    
                    if term_results:
                        ReportCard.objects.update_or_create(
                            student=student.user,
                            term=current_term,
                            academic_class=academic_class,
                            defaults={
                                'average_score': term_results.average_score,
                                'total_subjects': term_results.total_subjects,
                            }
                        )
        except IntegrityError:
            messages.error(request, 'An error occurred while generating report cards. Please try again.')
            return redirect('school:admin_dashboard')
        
        messages.success(request, f'Report cards generated for {students.count()} students.')
    return redirect('school:admin_dashboard')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_parent_profiles(request):
    """Display parent profiles grouped by parent user with their linked children.

    Parents are displayed as cards, each listing their linked students with
    relationship, phone, email, and primary contact status. Uses pagination
    to limit 10 parents per page.
    """
    parent_profiles = ParentProfile.objects.all().select_related('parent', 'student', 'parent__profile', 'student__profile').order_by('parent__username', 'student__username')
    
    parents_with_children = {}
    for link in parent_profiles:
        parent_user = link.parent
        if parent_user not in parents_with_children:
            parents_with_children[parent_user] = {
                'user': parent_user,
                'profile': parent_user.profile,
                'links': [],
            }
        parents_with_children[parent_user]['links'].append(link)
    
    parents_list = list(parents_with_children.values())
    
    paginator = Paginator(parents_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'school/admin_parent_profiles.html', {
        'page_obj': page_obj,
        'parents': page_obj,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_add_child_to_parent(request, parent_id):
    """Add a child (student) link to an existing parent account.

    GET: Display form to select a student and set relationship details.
    POST: Create a ParentProfile linking the parent to the selected student.
    """
    parent_user = get_object_or_404(User.objects.select_related('profile'), pk=parent_id, profile__role=Profile.ROLE_PARENT)
    
    class_id = request.GET.get('class_id') or request.POST.get('class_id')
    student_id = request.GET.get('student_id') or request.POST.get('student_id')
    selected_student = None
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        relationship = request.POST.get('relationship', 'guardian')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        is_primary = request.POST.get('is_primary') == 'on'
        
        if student_id:
            try:
                student = User.objects.get(pk=student_id, profile__role=Profile.ROLE_STUDENT, profile__status=Profile.STATUS_ACTIVE)
                parent_link = ParentProfile.objects.create(
                    parent=parent_user,
                    student=student,
                    relationship=relationship,
                    phone=phone,
                    email=email,
                    is_primary=is_primary,
                )
                create_audit_log(
                    user=request.user,
                    action='create',
                    model_name='ParentProfile',
                    obj=parent_link,
                    request=request
                )
                messages.success(request, f'Child linked to {parent_user.get_full_name() or parent_user.username} successfully.')
            except User.DoesNotExist:
                messages.error(request, 'Invalid student selected.')
            except IntegrityError:
                messages.error(request, 'An error occurred while linking the child. Please try again.')
        else:
            messages.error(request, 'Please select a student.')
        
        return redirect('school:admin_parent_profiles')
    
    classes = AcademicClass.objects.filter(is_active=True).order_by('name')
    students = User.objects.filter(profile__role=Profile.ROLE_STUDENT, profile__status=Profile.STATUS_ACTIVE).select_related('profile', 'profile__academic_class').order_by('username')
    
    if class_id:
        students = students.filter(profile__academic_class_id=class_id)
    
    if student_id and class_id:
        try:
            selected_student = User.objects.get(
                pk=student_id,
                profile__role=Profile.ROLE_STUDENT,
                profile__status=Profile.STATUS_ACTIVE,
                profile__academic_class_id=class_id
            )
        except User.DoesNotExist:
            selected_student = None
    
    return render(request, 'school/admin_add_child_to_parent.html', {
        'parent': parent_user,
        'students': students,
        'classes': classes,
        'selected_class_id': class_id,
        'selected_student': selected_student,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_parent_profile(request, pk):
    parent = get_object_or_404(ParentProfile, pk=pk)
    if request.method == 'POST':
        try:
            parent_repr = str(parent)
            parent.delete()
            create_audit_log(
                user=request.user,
                action='delete',
                model_name='ParentProfile',
                object_id=str(pk),
                object_repr=parent_repr,
                request=request
            )
            messages.success(request, 'Parent profile deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this parent profile because it has related records. Remove them first.')
    return redirect('school:admin_parent_profiles')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_events(request):
    events = SchoolEvent.objects.all().order_by('-start_date')
    if request.method == 'POST':
        form = SchoolEventForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Event added successfully.')
                return redirect('school:admin_events')
            except IntegrityError:
                messages.error(request, 'An error occurred while adding the event. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SchoolEventForm()
    return render(request, 'school/admin_events.html', {'events': events, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_event(request, pk):
    event = get_object_or_404(SchoolEvent, pk=pk)
    if request.method == 'POST':
        try:
            event_repr = str(event)
            event.delete()
            create_audit_log(
                user=request.user,
                action='delete',
                model_name='SchoolEvent',
                obj=event,
                object_id=str(pk),
                object_repr=event_repr,
                request=request
            )
            messages.success(request, 'Event deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this event because it has related records. Remove them first.')
    return redirect('school:admin_events')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_fees(request):
    fees = Fee.objects.all().select_related('academic_class', 'term').order_by('-created_at')
    if request.method == 'POST':
        form = FeeForm(request.POST)
        if form.is_valid():
            try:
                fee = form.save()
                create_audit_log(
                    user=request.user,
                    action='create',
                    model_name='Fee',
                    obj=fee,
                    request=request
                )
                messages.success(request, 'Fee added successfully.')
                return redirect('school:admin_fees')
            except IntegrityError:
                messages.error(request, 'An error occurred while adding the fee. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FeeForm()
    return render(request, 'school/admin_fees.html', {'fees': fees, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_fee(request, pk):
    fee = get_object_or_404(Fee, pk=pk)
    if request.method == 'POST':
        try:
            fee_repr = str(fee)
            fee.delete()
            create_audit_log(
                user=request.user,
                action='delete',
                model_name='Fee',
                obj=fee,
                object_id=str(pk),
                object_repr=fee_repr,
                request=request
            )
            messages.success(request, 'Fee deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this fee because it has related records. Remove them first.')
    return redirect('school:admin_fees')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_payments(request):
    payments = Payment.objects.all().select_related('student', 'fee').order_by('-created_at')
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = form.save(commit=False)
                payment.amount = payment.fee.amount
                payment.save()
                create_audit_log(
                    user=request.user,
                    action='create',
                    model_name='Payment',
                    obj=payment,
                    request=request
                )
                messages.success(request, 'Payment recorded successfully.')
                return redirect('school:admin_payments')
            except IntegrityError:
                messages.error(request, 'An error occurred while recording the payment. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PaymentForm()
    return render(request, 'school/admin_payments.html', {'payments': payments, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_payment(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    if request.method == 'POST':
        try:
            payment_repr = str(payment)
            payment.delete()
            create_audit_log(
                user=request.user,
                action='delete',
                model_name='Payment',
                obj=payment,
                object_id=str(pk),
                object_repr=payment_repr,
                request=request
            )
            messages.success(request, 'Payment deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this payment because it has related records. Remove them first.')
    return redirect('school:admin_payments')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_audit_logs(request):
    logs = AuditLog.objects.all().select_related('user').order_by('-timestamp')[:500]
    return render(request, 'school/admin_audit_logs.html', {'logs': logs})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_export_students_csv(request):
    students = Profile.objects.filter(
        role=Profile.ROLE_STUDENT
    ).select_related('user', 'academic_class').order_by('academic_class__name', 'user__username')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['Username', 'Full Name', 'Matric Number', 'Class', 'Email', 'Phone', 'Gender', 'Activated'])
    for student in students:
        writer.writerow([
            student.user.username,
            student.user.get_full_name() or student.user.username,
            student.admission_number or 'N/A',
            student.academic_class.name if student.academic_class else 'N/A',
            student.user.email or 'N/A',
            student.phone or 'N/A',
            student.get_gender_display() if student.gender else 'N/A',
            'Yes' if student.is_activated else 'No',
        ])
    return response


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_export_results_csv(request):
    test_results = TestResult.objects.all().select_related('student', 'test', 'test__subject', 'test__term', 'test__academic_class').order_by('student__username', 'test__term', 'test__date')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="results.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student', 'Matric Number', 'Class', 'Subject', 'Term', 'Test/Exam', 'Title', 'Score', 'Max Score', 'Percentage', 'Date'])
    for tr in test_results:
        writer.writerow([
            tr.student.get_full_name() or tr.student.username,
            tr.student.profile.admission_number or 'N/A',
            tr.test.academic_class.name,
            tr.test.subject.name,
            tr.test.term.get_name_display(),
            'Test',
            tr.test.title,
            tr.score,
            tr.test.max_score,
            tr.get_percentage(),
            tr.submitted_at.date(),
        ])
    return response


def calculate_term_results(term, academic_class=None):
    """
    Calculate term results for all students in a given term and optional class.
    Returns the number of students processed.
    """
    from accounts.models import Profile
    from django.db.models import Avg, Count
    
    # Get students with results in this term
    students_qs = User.objects.filter(
        profile__role=Profile.ROLE_STUDENT,
        test_results__test__term=term,
    ).distinct()
    
    if academic_class:
        students_qs = students_qs.filter(profile__academic_class=academic_class)
    
    count = 0
    for student in students_qs:
        # Get all test and exam results for this student in this term
        test_results = TestResult.objects.filter(
            student=student,
            test__term=term
        ).select_related('test__subject')
        
        exam_results = ExamResult.objects.filter(
            student=student,
            exam__term=term
        ).select_related('exam__subject')
        
        # Calculate average per subject
        subject_scores = {}
        
        for tr in test_results:
            subject = tr.test.subject
            if subject not in subject_scores:
                subject_scores[subject] = {'test': [], 'exam': []}
            subject_scores[subject]['test'].append(float(tr.score))
        
        for er in exam_results:
            subject = er.exam.subject
            if subject not in subject_scores:
                subject_scores[subject] = {'test': [], 'exam': []}
            subject_scores[subject]['exam'].append(float(er.score))
        
        # Calculate average per subject (simple average of all scores)
        total_score = 0
        subjects_count = 0
        
        for subject, scores in subject_scores.items():
            test_avg = sum(scores['test']) / len(scores['test']) if scores['test'] else 0
            exam_avg = sum(scores['exam']) / len(scores['exam']) if scores['exam'] else 0
            
            # Simple average of test and exam scores
            if scores['test'] and scores['exam']:
                subject_avg = (test_avg + exam_avg) / 2
            elif scores['test']:
                subject_avg = test_avg
            elif scores['exam']:
                subject_avg = exam_avg
            else:
                subject_avg = 0
            
            total_score += subject_avg
            subjects_count += 1
        
        if subjects_count > 0:
            average_score = round(total_score / subjects_count, 2)
            
            # Count total assessments (tests + exams) for total_subjects
            total_assessments = test_results.count() + exam_results.count()
            
            TermResult.objects.update_or_create(
                student=student,
                term=term,
                defaults={
                    'academic_class': student.profile.academic_class,
                    'average_score': average_score,
                    'total_subjects': total_assessments,
                }
            )
            count += 1
    
    return count
