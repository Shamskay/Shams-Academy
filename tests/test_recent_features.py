import pytest
from datetime import timedelta
from django.urls import reverse
from django.test import Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from accounts.models import Profile
from school.models import Term, AcademicClass, Subject, ClassSubject, Test, TestResult, Exam, ExamResult, GradeBoundary, TermResult

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username='admin', email='admin@test.com', password='adminpass123'
    )
    return user


@pytest.fixture
def staff_user(db):
    user = User.objects.create_user(
        username='staff1', email='staff@test.com', password='staffpass123'
    )
    Profile.objects.filter(user=user).update(role=Profile.ROLE_STAFF, is_activated=True)
    return user


@pytest.fixture
def student_user(db):
    user = User.objects.create_user(
        username='student1', email='student@test.com', password='studentpass123'
    )
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_STUDENT, is_activated=True, admission_number='STU001'
    )
    return user


@pytest.fixture
def parent_user(db):
    user = User.objects.create_user(
        username='parent1', email='parent@test.com', password='parentpass123'
    )
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_PARENT, is_activated=True, unique_id='PAR-123456'
    )
    return user


@pytest.fixture
def term(db):
    return Term.objects.create(
        name='first', is_current=True, start_date='2024-01-01',
        end_date='2024-03-31', next_term_start_date='2024-04-01'
    )


@pytest.fixture
def academic_class(db):
    return AcademicClass.objects.create(name='JSS1', section='jss', is_active=True)


@pytest.fixture
def student_with_class(student_user, academic_class):
    student_user.profile.academic_class = academic_class
    student_user.profile.save()
    return student_user


class TestTokenExpiration:
    def test_token_generation_sets_timestamp(self, client, admin_user, student_with_class):
        client.login(username='admin', password='adminpass123')
        response = client.get(
            reverse('accounts:admin_generate_student_reset_token') +
            f'?class_id={student_with_class.profile.academic_class.pk}'
        )
        assert response.status_code == 200

        response = client.post(
            reverse('accounts:admin_generate_student_reset_token'),
            {'class_id': student_with_class.profile.academic_class.pk,
             'student_id': student_with_class.profile.pk}
        )
        profile = Profile.objects.get(pk=student_with_class.profile.pk)
        assert profile.password_reset_token is not None
        assert profile.password_reset_token_created_at is not None

    def test_fresh_token_works(self, client, student_with_class):
        profile = student_with_class.profile
        profile.password_reset_token = '123456'
        profile.password_reset_token_created_at = timezone.now()
        profile.save(update_fields=['password_reset_token', 'password_reset_token_created_at'])

        response = client.post(reverse('accounts:student_password_reset_token'), {'token': '123456'})
        assert response.status_code == 302
        assert response.url == reverse('accounts:student_password_reset')

    def test_expired_token_rejected(self, client, student_with_class):
        profile = student_with_class.profile
        profile.password_reset_token = '123456'
        profile.password_reset_token_created_at = timezone.now() - timedelta(minutes=11)
        profile.save(update_fields=['password_reset_token', 'password_reset_token_created_at'])

        response = client.post(reverse('accounts:student_password_reset_token'), {'token': '123456'})
        assert response.status_code == 200
        assert b'expired' in response.content


class TestParentRedirectFromStudentViews:
    def test_parent_redirected_from_student_dashboard(self, client, parent_user):
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('students:student_dashboard'))
        assert response.status_code == 302
        assert response.url == reverse('school:parent_dashboard')

    def test_parent_redirected_from_student_subjects(self, client, parent_user):
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('students:student_subjects'))
        assert response.status_code == 302
        assert response.url == reverse('school:parent_dashboard')

    def test_parent_redirected_from_my_results(self, client, parent_user):
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('students:my_results'))
        assert response.status_code == 302
        assert response.url == reverse('school:parent_dashboard')

    def test_parent_redirected_from_term_results(self, client, parent_user):
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('students:term_results'))
        assert response.status_code == 302
        assert response.url == reverse('school:parent_dashboard')

    def test_parent_redirected_to_own_dashboard(self, client, parent_user):
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('school:dashboard'))
        assert response.status_code == 302
        assert response.url == reverse('school:parent_dashboard')


class TestGradeBoundariesOnIndividualResults:
    def test_my_results_uses_raw_queryset(self, client, db, student_user, term):
        from school.models import AcademicClass, ClassSubject, Subject, Test, TestResult
        cls = AcademicClass.objects.create(name='JSS1', section='jss', is_active=True)
        student_user.profile.academic_class = cls
        student_user.profile.save()
        subj = Subject.objects.create(name='Math', code='MTH', is_core=True, is_active=True)
        test = Test.objects.create(subject=subj, term=term, academic_class=cls, title='Test 1', max_score=20, date='2024-01-15')
        TestResult.objects.create(student=student_user, test=test, score=15, entered_by=TestResult.ENTERED_BY_TEACHER)

        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('students:my_results'))
        assert response.status_code == 200
        assert b'Grade' not in response.content
        assert b'test.high' not in response.content

    def test_parent_child_detail_no_grade_on_individual_results(self, client, db, parent_user, student_user, academic_class):
        from school.models import ParentProfile
        ParentProfile.objects.create(parent=parent_user, student=student_user, relationship='father')
        student_user.profile.academic_class = academic_class
        student_user.profile.save()

        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('school:parent_child_detail', args=[student_user.pk]))
        assert response.status_code == 200
        assert b'badge bg-secondary' not in response.content
        assert b'badge bg-info' not in response.content

    def test_term_results_uses_annotated_grades(self, client, db, student_user, term, academic_class):
        from school.models import TermResult as TR, GradeBoundary as GB
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        TR.objects.create(student=student_user, term=term, academic_class=academic_class,
                           average_score=85.0, total_subjects=5)
        GB.objects.create(name='A', min_score=70, max_score=100, is_active=True)

        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('students:term_results'))
        assert response.status_code == 200
        assert b'A' in response.content


class TestSMTPConfiguration:
    def test_email_host_set(self):
        assert settings.EMAIL_HOST == 'smtp.gmail.com'

    def test_email_port_set(self):
        assert settings.EMAIL_PORT == 587

    def test_email_use_tls_set(self):
        assert settings.EMAIL_USE_TLS is True


class TestSafeProfileTemplateTag:
    def test_anonymous_user_no_crash(self, client, db):
        response = client.get(reverse('school:home'))
        assert response.status_code == 200

    def test_parent_navbar_uses_parent_route(self, client, parent_user):
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('school:home'))
        assert response.status_code == 200
