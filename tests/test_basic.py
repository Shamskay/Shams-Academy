import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Profile
from school.models import Term, AcademicClass, Subject, ClassSubject

User = get_user_model()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass123'
    )
    return user


@pytest.fixture
def staff_user(db):
    user = User.objects.create_user(
        username='staff1',
        email='staff@test.com',
        password='staffpass123'
    )
    Profile.objects.filter(user=user).update(role=Profile.ROLE_STAFF, is_activated=True)
    return user


@pytest.fixture
def student_user(db):
    user = User.objects.create_user(
        username='student1',
        email='student@test.com',
        password='studentpass123'
    )
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_STUDENT,
        is_activated=True,
        admission_number='STU001'
    )
    return user


@pytest.fixture
def term(db):
    return Term.objects.create(
        name='first',
        is_current=True,
        start_date='2024-01-01',
        end_date='2024-03-31',
        next_term_start_date='2024-04-01'
    )


@pytest.fixture
def academic_class(db):
    return AcademicClass.objects.create(name='JSS1', section='jss', is_active=True)


@pytest.fixture
def subject(db):
    return Subject.objects.create(name='Mathematics', code='MTH', is_core=True, is_active=True)


@pytest.fixture
def class_subject(db, academic_class, subject, staff_user):
    return ClassSubject.objects.create(
        academic_class=academic_class,
        subject=subject,
        teacher=staff_user,
        is_active=True
    )


class TestPublicPages:
    def test_home_page_loads(self, client, db):
        response = client.get(reverse('school:home'))
        assert response.status_code == 200

    def test_login_page_loads(self, client):
        response = client.get(reverse('accounts:login'))
        assert response.status_code == 200

    def test_password_reset_page_loads(self, client):
        response = client.get(reverse('accounts:password_reset'))
        assert response.status_code == 200


class TestAdminAccess:
    def test_admin_dashboard_requires_superuser(self, client, student_user):
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('school:admin_dashboard'))
        assert response.status_code == 302

    def test_admin_dashboard_loads_for_superuser(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_dashboard'))
        assert response.status_code == 200


class TestStaffAccess:
    def test_staff_dashboard_requires_staff(self, client, student_user):
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('staff:staff_dashboard'))
        assert response.status_code == 302

    def test_staff_dashboard_loads_for_staff(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('staff:staff_dashboard'))
        assert response.status_code == 200


class TestStudentAccess:
    def test_student_dashboard_requires_student(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('students:student_dashboard'))
        assert response.status_code == 302

    def test_student_dashboard_loads_for_student(self, client, student_user):
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('students:student_dashboard'))
        assert response.status_code == 200


class TestAssessmentCreation:
    def test_staff_can_create_test(self, client, db, staff_user, term, academic_class, subject, class_subject):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('assessments:staff_create_test'))
        assert response.status_code == 200

        data = {
            'title': 'Test 1',
            'subject': subject.pk,
            'term': term.pk,
            'academic_class': academic_class.pk,
            'max_score': 20,
            'date': '2024-01-15',
            'instructions': 'Test instructions',
        }
        response = client.post(reverse('assessments:staff_create_test'), data)
        assert response.status_code == 302

    def test_staff_can_create_exam(self, client, db, staff_user, term, academic_class, subject, class_subject):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('assessments:staff_create_exam'))
        assert response.status_code == 200

        data = {
            'title': 'Exam 1',
            'subject': subject.pk,
            'term': term.pk,
            'academic_class': academic_class.pk,
            'max_score': 70,
            'date': '2024-03-15',
            'instructions': 'Exam instructions',
        }
        response = client.post(reverse('assessments:staff_create_exam'), data)
        assert response.status_code == 302

    def test_staff_can_enter_test_result(self, client, db, staff_user, term, academic_class, subject, class_subject, student_user):
        from school.models import Test
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        test = Test.objects.create(
            subject=subject,
            term=term,
            academic_class=academic_class,
            title='Test 1',
            max_score=20,
            date='2024-01-15'
        )
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('assessments:staff_enter_test_result'))
        assert response.status_code == 200

        data = {
            'student': student_user.pk,
            'test': test.pk,
            'academic_class': academic_class.pk,
            'score': 15,
        }
        response = client.post(reverse('assessments:staff_enter_test_result'), data)
        assert response.status_code == 200
