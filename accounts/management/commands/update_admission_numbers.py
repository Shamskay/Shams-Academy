import random
import string

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from accounts.models import Profile


class Command(BaseCommand):
    help = 'Update existing student admission numbers to the new ADM-{initials}/{digits}/{year} format'

    def handle(self, *args, **options):
        initials = getattr(settings, 'SCHOOL_INITIALS', 'SKA')
        year = timezone.now().strftime('%Y')
        students = Profile.objects.filter(role=Profile.ROLE_STUDENT)

        updated = 0
        for profile in students:
            code = ''.join(random.choices(string.digits, k=4))
            new_admission = f"ADM-{initials}/{code}/{year}"
            if profile.admission_number != new_admission:
                old = profile.admission_number
                profile.admission_number = new_admission
                profile.save(update_fields=['admission_number'])
                self.stdout.write(f'Updated {profile.user.username}: {old} -> {new_admission}')
                updated += 1
            else:
                self.stdout.write(f'Skipping {profile.user.username}: already up to date')

        self.stdout.write(self.style.SUCCESS(f'Updated {updated} student admission number(s).'))
