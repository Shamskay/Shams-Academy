from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView
import uuid

from .forms import StudentSignupForm, StudentActivationTokenForm, StudentActivationForm, ProfileUpdateForm, StaffRegistrationForm, ParentRegistrationForm
from .models import Profile
from .backends import MatricOrUniqueIDBackend


def get_user_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def role_selection(request):
    return render(request, 'accounts/role_selection.html')


def student_signup(request):
    token_in_session = request.session.get('student_activation_token')
    profile = None
    
    if token_in_session:
        try:
            profile = Profile.objects.get(activation_token=token_in_session, is_activated=False)
        except Profile.DoesNotExist:
            request.session.pop('student_activation_token', None)
            messages.error(request, 'Invalid or expired activation token. Please contact your admin.')
            return redirect('accounts:student_signup')

    if request.method == 'POST':
        if not profile:
            token_form = StudentActivationTokenForm(request.POST)
            if token_form.is_valid():
                token = token_form.cleaned_data['token']
                try:
                    profile = Profile.objects.get(activation_token=token, is_activated=False)
                    request.session['student_activation_token'] = token
                    messages.success(request, 'Token validated. Please complete your registration.')
                    return redirect('accounts:student_signup')
                except Profile.DoesNotExist:
                    messages.error(request, 'Invalid or expired activation token.')
            registration_form = None
        else:
            token_form = None
            registration_form = StudentActivationForm(request.POST)
            if registration_form.is_valid():
                try:
                    with transaction.atomic():
                        user = profile.user
                        user.email = registration_form.cleaned_data.get('email', '')
                        user.set_password(registration_form.cleaned_data['password1'])
                        user.save()

                        profile.is_activated = True
                        profile.activation_token = None
                        profile.save()

                        request.session.pop('student_activation_token', None)
                        login(request, user, backend='accounts.backends.MatricOrUniqueIDBackend')
                        messages.success(request, 'Account activated successfully.')
                        return redirect('school:dashboard')
                except IntegrityError:
                    messages.error(request, 'An error occurred while activating your account. Please try again.')
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        token_form = StudentActivationTokenForm() if not profile else None
        registration_form = StudentActivationForm() if profile else None

    context = {
        'token_form': token_form,
        'registration_form': registration_form,
        'step': 'token' if not profile else 'register',
    }
    return render(request, 'accounts/signup.html', context)


def staff_register(request):
    if request.user.is_authenticated:
        return redirect('school:dashboard')

    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user, backend='accounts.backends.MatricOrUniqueIDBackend')
                messages.success(request, 'Staff account activated successfully.')
                return redirect('staff:staff_dashboard')
            except IntegrityError:
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = StaffRegistrationForm()
    return render(request, 'accounts/staff_register.html', {'form': form})


def parent_register(request):
    if request.user.is_authenticated:
        return redirect('school:dashboard')

    if request.method == 'POST':
        form = ParentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user, backend='accounts.backends.MatricOrUniqueIDBackend')
                messages.success(request, 'Parent account activated successfully.')
                return redirect('school:parent_dashboard')
            except IntegrityError:
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ParentRegistrationForm()
    return render(request, 'accounts/parent_register.html', {'form': form})


def student_activate(request, token):
    profile = get_object_or_404(Profile, activation_token=token, is_activated=False)
    
    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')

        if not password1 or password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'accounts/student_activate.html', {'token': token, 'profile': profile})

        try:
            with transaction.atomic():
                user = profile.user
                user.set_password(password1)
                user.email = email
                user.save()

                profile.email = email
                profile.phone = phone
                profile.is_activated = True
                profile.activation_token = None
                profile.save()

                login(request, user, backend='accounts.backends.MatricOrUniqueIDBackend')
                messages.success(request, 'Account activated successfully. You can now log in with your Matric Number.')
                return redirect('school:dashboard')
        except IntegrityError:
            messages.error(request, 'An error occurred while activating your account. Please try again.')

    return render(request, 'accounts/student_activate.html', {'token': token, 'profile': profile})


@login_required
def dashboard(request):
    return redirect('school:dashboard')


@login_required
def profile_update(request):
    profile = get_user_profile(request.user)
    if not profile:
        messages.error(request, 'Profile not found. Please contact the admin.')
        return redirect('school:dashboard')
    
    if request.method == 'POST':
        form = ProfileUpdateForm(
            request.POST,
            request.FILES,
            instance=profile,
        )
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    email = form.cleaned_data.get('email')
                    request.user.email = email
                    request.user.first_name = form.cleaned_data.get('first_name')
                    request.user.last_name = form.cleaned_data.get('last_name')
                    request.user.save()
                    messages.success(request, 'Profile updated successfully.')
                    return redirect('accounts:profile')
            except IntegrityError:
                messages.error(request, 'An error occurred while updating your profile. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial = {
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
        form = ProfileUpdateForm(instance=profile, initial=initial)
    return render(request, 'accounts/profile_form.html', {'form': form})


class ProfileDetailView(LoginRequiredMixin, DetailView):
    model = Profile
    template_name = 'accounts/profile.html'

    def get_object(self, queryset=None):
        try:
            return self.request.user.profile
        except Profile.DoesNotExist:
            Profile.objects.get_or_create(user=self.request.user)
            return self.request.user.profile
