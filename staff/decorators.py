from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.contrib.auth.decorators import login_required, user_passes_test


def staff_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from accounts.models import Profile
        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return redirect('school:home')
        if profile.role != Profile.ROLE_STAFF:
            return redirect('school:home')
        if not profile.is_activated:
            messages.error(request, 'Your account is pending activation. Please contact the admin.')
            return redirect('staff:staff_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
