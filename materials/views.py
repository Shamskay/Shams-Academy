from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import IntegrityError

from accounts.models import Profile
from .forms import StudyMaterialForm
from school.models import StudyMaterial, Subject, Term
from staff.decorators import staff_required


def get_user_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


@staff_required
def staff_upload_material(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('staff:staff_dashboard')
    
    if request.method == 'POST':
        form = StudyMaterialForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            try:
                material = form.save(commit=False)
                material.uploaded_by = request.user
                material.save()
                messages.success(request, 'Material uploaded successfully.')
                return redirect('staff:staff_dashboard')
            except IntegrityError:
                messages.error(request, 'An error occurred while uploading the material. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StudyMaterialForm(user=request.user)
    return render(request, 'materials/staff_upload_material.html', {'form': form})


@staff_required
def staff_manage_materials(request):
    materials = StudyMaterial.objects.filter(uploaded_by=request.user).select_related('subject', 'academic_class', 'term').order_by('-created_at')
    return render(request, 'materials/staff_manage_materials.html', {'materials': materials})


@staff_required
def staff_delete_material(request, pk):
    if request.method == 'POST':
        material = get_object_or_404(StudyMaterial, pk=pk, uploaded_by=request.user)
        try:
            material.delete()
            messages.success(request, 'Material deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this material.')
    return redirect('materials:staff_manage_materials')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_manage_materials(request):
    materials = StudyMaterial.objects.all().select_related('subject', 'academic_class', 'term', 'uploaded_by').order_by('-created_at')
    return render(request, 'materials/admin_manage_materials.html', {'materials': materials})


@login_required
def student_materials(request, subject_id):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    if profile.role == Profile.ROLE_STAFF or request.user.is_superuser:
        return redirect('staff:staff_dashboard')

    subject = get_object_or_404(Subject, pk=subject_id)
    current_term = Term.objects.filter(is_current=True).first()

    materials = StudyMaterial.objects.filter(
        subject=subject, term=current_term, is_active=True
    ).select_related('uploaded_by', 'term').order_by('-created_at')

    context = {
        'subject': subject,
        'current_term': current_term,
        'materials': materials,
    }
    return render(request, 'materials/student_materials.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_delete_material(request, pk):
    material = get_object_or_404(StudyMaterial, pk=pk)
    if request.method == 'POST':
        try:
            material.delete()
            messages.success(request, 'Material deleted successfully.')
        except IntegrityError:
            messages.error(request, 'Cannot delete this material because it has related records.')
    return redirect('materials:admin_manage_materials')
