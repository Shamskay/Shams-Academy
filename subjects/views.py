from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError

from accounts.models import Profile
from school.forms import (
    TermForm, AcademicClassForm, SubjectForm, ClassSubjectForm, ClassTeacherForm
)
from school.models import Term, AcademicClass, Subject, ClassSubject, ClassTeacher


def get_user_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_terms(request):
    terms = Term.objects.all().order_by('name')
    if request.method == 'POST':
        form = TermForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Term created successfully.')
                return redirect('subjects:admin_terms')
            except IntegrityError:
                messages.error(request, 'An error occurred while creating the term. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TermForm()
    return render(request, 'subjects/admin_terms.html', {'terms': terms, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_classes(request):
    classes = AcademicClass.objects.all().order_by('section', 'name')
    if request.method == 'POST':
        form = AcademicClassForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Class created successfully.')
                return redirect('subjects:admin_classes')
            except IntegrityError:
                messages.error(request, 'An error occurred while creating the class. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AcademicClassForm()
    return render(request, 'subjects/admin_classes.html', {'classes': classes, 'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_subjects(request):
    subjects = Subject.objects.all().order_by('code')
    editing_subject = None
    if request.method == 'POST':
        if 'edit_pk' in request.POST:
            editing_subject = get_object_or_404(Subject, pk=request.POST.get('edit_pk'))
            form = SubjectForm(request.POST, instance=editing_subject)
        else:
            form = SubjectForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Subject saved successfully.')
                return redirect('subjects:admin_subjects')
            except IntegrityError:
                messages.error(request, 'An error occurred while saving the subject. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SubjectForm()
    return render(request, 'subjects/admin_subjects.html', {'subjects': subjects, 'form': form, 'editing_subject': editing_subject})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_edit_subject(request, pk):
    if request.method != 'POST':
        return redirect('subjects:admin_subjects')
    subject = get_object_or_404(Subject, pk=pk)
    form = SubjectForm(request.POST, instance=subject)
    if form.is_valid():
        try:
            form.save()
            messages.success(request, 'Subject updated successfully.')
        except IntegrityError:
            messages.error(request, 'An error occurred while updating the subject. Please try again.')
    else:
        messages.error(request, 'Please correct the errors below.')
    return redirect('subjects:admin_subjects')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_subject(request, pk):
    if request.method != 'POST':
        return redirect('subjects:admin_subjects')
    subject = get_object_or_404(Subject, pk=pk)
    try:
        subject.delete()
        messages.success(request, 'Subject deleted successfully.')
    except IntegrityError:
        messages.error(request, 'Cannot delete this subject because it is in use.')
    return redirect('subjects:admin_subjects')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_class_subjects(request):
    class_subjects = ClassSubject.objects.all().select_related('academic_class', 'subject', 'teacher')
    if request.method == 'POST':
        form = ClassSubjectForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Class subject assigned successfully.')
                return redirect('subjects:admin_class_subjects')
            except IntegrityError:
                messages.error(request, 'An error occurred while assigning the class subject. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClassSubjectForm()
    return render(request, 'subjects/admin_class_subjects.html', {
        'class_subjects': class_subjects, 'form': form
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_class_teachers(request):
    class_teachers = ClassTeacher.objects.all().select_related('academic_class', 'teacher')
    if request.method == 'POST':
        form = ClassTeacherForm(request.POST)
        if form.is_valid():
            academic_class = form.cleaned_data['academic_class']
            teacher = form.cleaned_data['teacher']
            existing = ClassTeacher.objects.filter(academic_class=academic_class, is_active=True).first()
            if existing:
                if existing.teacher == teacher:
                    messages.warning(request, f'{teacher.get_full_name() or teacher.username} is already the class teacher for {academic_class.name}.')
                else:
                    messages.error(request, f'{academic_class.name} already has a class teacher: {existing.teacher.get_full_name() or existing.teacher.username}. Remove them first before assigning a new one.')
            else:
                try:
                    form.save()
                    messages.success(request, 'Class teacher assigned successfully.')
                except IntegrityError:
                    messages.error(request, 'An error occurred while assigning the class teacher. Please try again.')
            return redirect('subjects:admin_class_teachers')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ClassTeacherForm()
    return render(request, 'subjects/admin_class_teachers.html', {
        'class_teachers': class_teachers, 'form': form
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_remove_class_teacher(request, pk):
    if request.method != 'POST':
        return redirect('subjects:admin_class_teachers')
    class_teacher = get_object_or_404(ClassTeacher, pk=pk)
    try:
        class_teacher.delete()
        messages.success(request, f'{class_teacher.teacher.get_full_name() or class_teacher.teacher.username} removed from {class_teacher.academic_class.name}.')
    except IntegrityError:
        messages.error(request, 'Cannot remove this class teacher due to existing references.')
    return redirect('subjects:admin_class_teachers')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_toggle_class_teacher(request, pk):
    if request.method != 'POST':
        return redirect('subjects:admin_class_teachers')
    class_teacher = get_object_or_404(ClassTeacher, pk=pk)
    class_teacher.is_active = not class_teacher.is_active
    class_teacher.save()
    status = 'activated' if class_teacher.is_active else 'deactivated'
    messages.success(request, f'{class_teacher.teacher.get_full_name() or class_teacher.teacher.username} {status} as class teacher for {class_teacher.academic_class.name}.')
    return redirect('subjects:admin_class_teachers')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_toggle_class_subject(request, pk):
    if request.method != 'POST':
        return redirect('subjects:admin_class_subjects')
    class_subject = get_object_or_404(ClassSubject, pk=pk)
    class_subject.is_active = not class_subject.is_active
    class_subject.save()
    status = 'activated' if class_subject.is_active else 'deactivated'
    teacher_name = class_subject.teacher.get_full_name() or class_subject.teacher.username if class_subject.teacher else 'No teacher'
    messages.success(request, f'{teacher_name} {status} as teacher for {class_subject}.')
    return redirect('subjects:admin_class_subjects')
