from django.db import transaction
from accounts.models import Profile
from school.models import AuditLog, GradeBoundary


def get_client_ip(request):
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    return None


def create_audit_log(user, action, model_name, obj, changes=None, request=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(obj.pk),
        object_repr=str(obj),
        changes=changes or {},
        ip_address=get_client_ip(request) if request else None,
    )


def get_user_profile(user):
    if not user or user.is_anonymous:
        return None
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def user_profile_context(request):
    return {'user_profile': get_user_profile(request.user)}


def get_grade_boundaries():
    return GradeBoundary.objects.filter(is_active=True).order_by('-min_score')


def annotate_grade(result_obj, score, boundaries=None):
    if boundaries is None:
        boundaries = get_grade_boundaries()
    for boundary in boundaries:
        if boundary.min_score <= score <= boundary.max_score:
            return boundary
    return None


def annotate_results(results, score_attr, boundaries=None):
    if boundaries is None:
        boundaries = get_grade_boundaries()
    return [
        {
            'result': obj,
            'grade': annotate_grade(obj, getattr(obj, score_attr), boundaries),
        }
        for obj in results
    ]


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default