from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Profile

User = get_user_model()


class Command(BaseCommand):
    help = 'Create the admin superuser with predefined credentials'

    def handle(self, *args, **options):
        username = 'Shamskay'
        password = 'Shams1992'
        email = 'admin@shamskayacademy.com'

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists.'))
            return

        user = User.objects.create_superuser(username=username, email=email, password=password)
        user.first_name = 'Shams'
        user.last_name = 'Kay'
        user.save()

        Profile.objects.filter(user=user).update(
            role=Profile.ROLE_ADMIN,
            phone='+234-800-000-0000',
            admission_number=None
        )

        self.stdout.write(self.style.SUCCESS(f'Admin user created successfully.'))
        self.stdout.write(self.style.SUCCESS(f'Username: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Password: {password}'))
        self.stdout.write(self.style.SUCCESS(f'Login at: /login/'))
