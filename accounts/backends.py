from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from accounts.models import Profile

UserModel = get_user_model()


class MatricOrUniqueIDBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if username is None or password is None:
            return None

        # Try username first
        try:
            user = UserModel._default_manager.get_by_natural_key(username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except UserModel.DoesNotExist:
            pass

        # Try matric number
        try:
            profile = Profile.objects.select_related('user').get(admission_number=username)
            if profile.user.check_password(password) and self.user_can_authenticate(profile.user):
                return profile.user
        except Profile.DoesNotExist:
            pass

        # Try unique ID
        try:
            profile = Profile.objects.select_related('user').get(unique_id=username)
            if profile.user.check_password(password) and self.user_can_authenticate(profile.user):
                return profile.user
        except Profile.DoesNotExist:
            pass

        return None
