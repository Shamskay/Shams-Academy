from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Profile
from school.models import AcademicClass


class StudentActivationTokenForm(forms.Form):
    token = forms.CharField(max_length=5, min_length=5, label='5-Digit Activation Token', widget=forms.TextInput(attrs={'placeholder': 'Enter 5-digit token'}))

    def clean_token(self):
        token = self.cleaned_data['token']
        if not Profile.objects.filter(activation_token=token, is_activated=False).exists():
            raise forms.ValidationError('Invalid or expired activation token.')
        return token


class StudentActivationForm(forms.Form):
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class BaseSignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})


class StudentSignupForm(BaseSignupForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        first_name = self.cleaned_data.get('first_name', '').strip()
        last_name = self.cleaned_data.get('last_name', '').strip()
        base_username = f"{first_name}.{last_name}".lower().replace(' ', '.') if first_name or last_name else f"student_{User.objects.count() + 1}"
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        user.username = username
        if commit:
            user.save()
        return user


class StaffRegistrationForm(forms.Form):
    unique_id = forms.CharField(max_length=50, label='Unique ID')
    username = forms.CharField(max_length=150, label='Username')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_unique_id(self):
        unique_id = self.cleaned_data['unique_id']
        try:
            profile = Profile.objects.get(unique_id=unique_id, role=Profile.ROLE_STAFF)
        except Profile.DoesNotExist:
            raise forms.ValidationError('Invalid Unique ID. Please contact admin.')
        if profile.user.has_usable_password():
            raise forms.ValidationError('This staff account has already been activated.')
        self.profile = profile
        return unique_id

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self):
        profile = self.profile
        user = profile.user
        user.username = self.cleaned_data['username']
        user.set_password(self.cleaned_data['password1'])
        user.save()
        Profile.objects.filter(user=user).update(is_activated=True)
        return user


class ParentRegistrationForm(forms.Form):
    invitation_code = forms.CharField(max_length=50, label='Invitation Code')
    username = forms.CharField(max_length=150, label='Username')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_invitation_code(self):
        code = self.cleaned_data['invitation_code']
        try:
            profile = Profile.objects.get(unique_id=code, role=Profile.ROLE_PARENT)
        except Profile.DoesNotExist:
            raise forms.ValidationError('Invalid invitation code. Please contact admin.')
        if profile.user.has_usable_password():
            raise forms.ValidationError('This parent account has already been activated.')
        self.profile = profile
        return code

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self):
        profile = self.profile
        user = profile.user
        user.username = self.cleaned_data['username']
        user.set_password(self.cleaned_data['password1'])
        user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = Profile
        fields = ('phone', 'date_of_birth', 'avatar')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ != 'ClearableFileInput':
                field.widget.attrs.update({'class': 'form-control'})


class StudentPasswordResetTokenForm(forms.Form):
    """Admin form to generate password reset token for students"""
    token = forms.CharField(
        max_length=6, min_length=6, 
        label='6-Digit Reset Token', 
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit token'})
    )

    def clean_token(self):
        token = self.cleaned_data['token']
        try:
            profile = Profile.objects.get(password_reset_token=token, role=Profile.ROLE_STUDENT)
        except Profile.DoesNotExist:
            raise forms.ValidationError('Invalid or expired reset token.')
        
        if profile.password_reset_token_created_at:
            from datetime import timedelta
            if timezone.now() - profile.password_reset_token_created_at > timedelta(minutes=10):
                raise forms.ValidationError('This reset token has expired. Please ask the admin to generate a new one.')
        
        return token


class StudentPasswordResetForm(forms.Form):
    """Student form to reset password using admin token"""
    password1 = forms.CharField(widget=forms.PasswordInput, label='New Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class ParentOTPRequestForm(forms.Form):
    """Parent form to request OTP for password reset"""
    email = forms.EmailField(required=True, label='Registered Email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if not Profile.objects.filter(user__email=email, role=Profile.ROLE_PARENT).exists():
            raise forms.ValidationError('No parent account found with this email.')
        return email


class ParentOTPVerifyForm(forms.Form):
    """Parent form to verify OTP and reset password"""
    otp = forms.CharField(max_length=6, min_length=6, label='6-Digit OTP')
    password1 = forms.CharField(widget=forms.PasswordInput, label='New Password')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data
