from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

from .forms import StudentSignupForm, StudentActivationTokenForm, StudentActivationForm, ProfileUpdateForm, StaffRegistrationForm, ParentRegistrationForm
from django.contrib.auth.forms import AuthenticationForm
from . import views


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label
            })


app_name = 'accounts'

urlpatterns = [
    path('role/', views.role_selection, name='role_selection'),
    path('student/signup/', views.student_signup, name='student_signup'),
    path('student/activate/<str:token>/', views.student_activate, name='student_activate'),
    path('staff/register/', views.staff_register, name='staff_register'),
    path('parent/register/', views.parent_register, name='parent_register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_update, name='profile_update'),
    path('me/', views.ProfileDetailView.as_view(), name='profile'),
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html', redirect_authenticated_user=True,
        authentication_form=LoginForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/password_change.html',
        success_url=reverse_lazy('accounts:password_change_done')
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/password_change_done.html'
    ), name='password_change_done'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Student Password Reset (Admin Token)
    path('admin/student-reset-token/', views.admin_generate_student_reset_token, name='admin_generate_student_reset_token'),
    path('student/password-reset-token/', views.student_password_reset_token, name='student_password_reset_token'),
    path('student/password-reset/', views.student_password_reset, name='student_password_reset'),
]
