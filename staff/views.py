from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import transaction

from accounts.models import Profile
from school.forms import AdminCreateStaffForm
from school.models import ClassSubject, StudyMaterial, Test, Exam


def get_user_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


@login_required
def staff_dashboard(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role != Profile.ROLE_STAFF:
        return redirect('school:dashboard')
    if not profile.is_activated:
        messages.error(request, 'Your account is pending activation. Please contact the admin.')
        return redirect('school:home')

    teaching_assignments = ClassSubject.objects.filter(
        teacher=request.user, is_active=True
    ).select_related('academic_class', 'subject')

    materials = StudyMaterial.objects.filter(
        uploaded_by=request.user
    ).select_related('subject', 'term').order_by('-created_at')[:10]

    tests = Test.objects.filter(
        subject__class_subjects__teacher=request.user,
        is_active=True
    ).distinct().select_related('subject', 'term', 'academic_class').order_by('-date')[:10]

    exams = Exam.objects.filter(
        subject__class_subjects__teacher=request.user,
        is_active=True
    ).distinct().select_related('subject', 'term', 'academic_class').order_by('-date')[:10]

    context = {
        'user': request.user,
        'profile': profile,
        'teaching_assignments': teaching_assignments,
        'materials': materials,
        'tests': tests,
        'exams': exams,
    }
    return render(request, 'staff/staff_dashboard.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_create_staff(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    
    if request.method == 'POST':
        form = AdminCreateStaffForm(request.POST)
        if form.is_valid():
            unique_id = form.cleaned_data['unique_id']
            first_name = form.cleaned_data.get('first_name', '')
            last_name = form.cleaned_data.get('last_name', '')
            email = form.cleaned_data.get('email', '')
            phone = form.cleaned_data.get('phone', '')
            gender = form.cleaned_data.get('gender', '')

            if Profile.objects.filter(unique_id=unique_id).exists():
                messages.error(request, 'Unique ID already exists.')
            elif User.objects.filter(username=unique_id).exists():
                messages.error(request, 'A user with this Unique ID already exists.')
            else:
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=unique_id,
                            password=None,
                            first_name=first_name,
                            last_name=last_name,
                            email=email
                        )
                        user.set_unusable_password()
                        user.save()
                        Profile.objects.filter(user=user).update(
                            role=Profile.ROLE_STAFF,
                            unique_id=unique_id,
                            phone=phone,
                            gender=gender
                        )
                        messages.success(request, f'Staff created with Unique ID: {unique_id}. They can now register using this ID.')
                        return redirect('school:admin_dashboard')
                except IntegrityError:
                    messages.error(request, 'An error occurred while creating the staff. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AdminCreateStaffForm()

    return render(request, 'staff/admin_create_staff.html', {'form': form})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_staff(request):
    staff_members = Profile.objects.filter(
        role=Profile.ROLE_STAFF
    ).select_related('user').order_by('-created_at')
    return render(request, 'staff/admin_staff.html', {'staff_members': staff_members})


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_toggle_staff_status(request, pk):
    profile = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_STAFF)
    if request.method == 'POST':
        profile.is_activated = not profile.is_activated
        profile.save()
        status = 'active' if profile.is_activated else 'inactive'
        messages.success(request, f'Staff status updated to {status}.')
    return redirect('staff:admin_staff')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_staff(request, pk):
    if request.method == 'POST':
        profile = get_object_or_404(Profile, pk=pk, role=Profile.ROLE_STAFF)
        try:
            user = profile.user
            profile.delete()
            user.delete()
            messages.success(request, 'Staff removed successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this staff because they have related records. Remove them first.')
    return redirect('staff:admin_staff')
