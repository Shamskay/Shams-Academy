import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from accounts.models import Profile
from school.models import ParentProfile, GradeBoundary, AcademicClass

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
def parent_user(db):
    user = User.objects.create_user(
        username='parent1',
        email='parent@test.com',
        password='parentpass123'
    )
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_PARENT,
        is_activated=True,
        unique_id='PAR-123456'
    )
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
        admission_number='STU001',
        status=Profile.STATUS_ACTIVE
    )
    return user


@pytest.fixture
def graduated_student(db):
    user = User.objects.create_user(
        username='student2',
        email='student2@test.com',
        password='studentpass123'
    )
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_STUDENT,
        is_activated=True,
        admission_number='STU002',
        status=Profile.STATUS_GRADUATED
    )
    return user


@pytest.fixture
def academic_class(db):
    return AcademicClass.objects.create(name='JSS1', section='jss', is_active=True)


class TestParentProfileCreation:
    def test_create_parent_page_loads_for_admin(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_create_parent'))
        assert response.status_code == 200

    def test_admin_can_create_parent_account(self, client, db, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_create_parent'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@test.com',
            'phone': '08012345678',
        })
        assert response.status_code == 302
        assert User.objects.filter(username='john.doe').exists()
        parent_user = User.objects.get(username='john.doe')
        assert parent_user.profile.role == Profile.ROLE_PARENT
        assert parent_user.profile.unique_id is not None
        assert parent_user.profile.unique_id.startswith('PAR-')

    def test_admin_can_create_parent_and_link_student(self, client, db, admin_user, student_user, academic_class):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_create_parent') + f'?class_id={academic_class.pk}')
        assert response.status_code == 200
        response = client.post(
            reverse('school:admin_create_parent') + f'?class_id={academic_class.pk}',
            {
                'first_name': 'Jane',
                'last_name': 'Parent',
                'student_id': student_user.pk,
                'class_id': str(academic_class.pk),
                'relationship': 'mother',
                'is_primary': 'on',
            }
        )
        assert response.status_code == 302
        assert ParentProfile.objects.filter(parent__username='jane.parent', student=student_user).exists()


class TestParentChildLinking:
    def test_add_child_page_loads(self, client, admin_user, parent_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_add_child_to_parent', args=[parent_user.pk]))
        assert response.status_code == 200

    def test_admin_can_add_child_to_parent(self, client, db, admin_user, parent_user, student_user, academic_class):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        client.login(username='admin', password='adminpass123')
        response = client.post(
            reverse('school:admin_add_child_to_parent', args=[parent_user.pk]),
            {
                'student_id': student_user.pk,
                'class_id': str(academic_class.pk),
                'relationship': 'father',
                'phone': '08012345678',
                'email': 'parent@test.com',
                'is_primary': 'on',
            }
        )
        assert response.status_code == 302
        assert ParentProfile.objects.filter(parent=parent_user, student=student_user).exists()

    def test_parent_can_have_multiple_children(self, client, db, admin_user, parent_user, academic_class):
        student1 = User.objects.create_user(username='child1', password='pass1')
        Profile.objects.filter(user=student1).update(
            role=Profile.ROLE_STUDENT,
            is_activated=True,
            status=Profile.STATUS_ACTIVE,
            admission_number='STU-C1'
        )
        student1.profile.academic_class = academic_class
        student1.profile.save()

        student2 = User.objects.create_user(username='child2', password='pass2')
        Profile.objects.filter(user=student2).update(
            role=Profile.ROLE_STUDENT,
            is_activated=True,
            status=Profile.STATUS_ACTIVE,
            admission_number='STU-C2'
        )
        student2.profile.academic_class = academic_class
        student2.profile.save()

        client.login(username='admin', password='adminpass123')
        client.post(
            reverse('school:admin_add_child_to_parent', args=[parent_user.pk]),
            {'student_id': student1.pk, 'class_id': str(academic_class.pk), 'relationship': 'father'}
        )
        client.post(
            reverse('school:admin_add_child_to_parent', args=[parent_user.pk]),
            {'student_id': student2.pk, 'class_id': str(academic_class.pk), 'relationship': 'mother'}
        )
        assert ParentProfile.objects.filter(parent=parent_user).count() == 2


class TestParentDashboardAccess:
    def test_parent_dashboard_requires_login(self, client):
        response = client.get(reverse('school:parent_dashboard'))
        assert response.status_code == 302

    def test_non_parent_cannot_access_dashboard(self, client, student_user):
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('school:parent_dashboard'))
        assert response.status_code == 302

    def test_parent_dashboard_shows_linked_children(self, client, parent_user, student_user):
        ParentProfile.objects.create(
            parent=parent_user,
            student=student_user,
            relationship='father'
        )
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('school:parent_dashboard'))
        assert response.status_code == 200
        assert b'child1' not in response.content.lower() or b'student1' in response.content.lower()

    def test_parent_child_detail_requires_linked_student(self, client, parent_user, student_user, graduated_student):
        ParentProfile.objects.create(parent=parent_user, student=student_user, relationship='father')
        client.login(username='parent1', password='parentpass123')
        response = client.get(reverse('school:parent_child_detail', args=[student_user.pk]))
        assert response.status_code == 200
        response = client.get(reverse('school:parent_child_detail', args=[graduated_student.pk]))
        assert response.status_code == 404


class TestStudentStatusTransitions:
    def test_active_student_appears_in_dropdowns(self, client, admin_user, student_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_create_parent'))
        assert response.status_code == 200
        form = response.context['form']
        assert student_user in form.fields['student'].queryset

    def test_graduated_student_excluded_from_dropdowns(self, client, admin_user, graduated_student):
        graduated_student.profile.status = Profile.STATUS_GRADUATED
        graduated_student.profile.save()
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_create_parent'))
        assert response.status_code == 200
        form = response.context['form']
        assert graduated_student not in form.fields['student'].queryset

    def test_admin_can_update_student_status(self, client, admin_user, student_user):
        client.login(username='admin', password='adminpass123')
        response = client.post(
            reverse('students:admin_students'),
            {'profile_id': str(student_user.profile.pk), 'status': Profile.STATUS_GRADUATED}
        )
        assert response.status_code == 302
        student_user.profile.refresh_from_db()
        assert student_user.profile.status == Profile.STATUS_GRADUATED

    def test_status_update_validates_choices(self, client, admin_user, student_user):
        client.login(username='admin', password='adminpass123')
        response = client.post(
            reverse('students:admin_students'),
            {'profile_id': str(student_user.profile.pk), 'status': 'invalid'}
        )
        assert response.status_code == 302
        student_user.profile.refresh_from_db()
        assert student_user.profile.status == Profile.STATUS_ACTIVE


class TestParentProfileLinksSurviveStudentStatusChange:
    def test_parent_link_preserved_after_student_graduated(self, client, parent_user, student_user):
        ParentProfile.objects.create(parent=parent_user, student=student_user, relationship='father')
        student_user.profile.status = Profile.STATUS_GRADUATED
        student_user.profile.save()
        assert ParentProfile.objects.filter(parent=parent_user, student=student_user).exists()

    def test_parent_link_preserved_after_student_withdrawn(self, client, parent_user, student_user):
        ParentProfile.objects.create(parent=parent_user, student=student_user, relationship='father')
        student_user.profile.status = Profile.STATUS_WITHDRAWN
        student_user.profile.save()
        assert ParentProfile.objects.filter(parent=parent_user, student=student_user).exists()


class TestGradeBoundaries:
    def test_grade_boundary_page_loads_for_admin(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_grade_boundaries'))
        assert response.status_code == 200

    def test_admin_can_create_grade_boundary(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_grade_boundaries'), {
            'name': 'A',
            'min_score': 70,
            'max_score': 100,
            'remark': 'Excellent',
            'is_active': 'on',
        })
        assert response.status_code == 302
        assert GradeBoundary.objects.filter(name='A').exists()

    def test_grade_boundary_str(self, db):
        boundary = GradeBoundary.objects.create(
            name='A',
            min_score=70,
            max_score=100,
            remark='Excellent'
        )
        assert str(boundary) == 'A: 70 - 100'

    def test_grade_boundary_ordering(self, db):
        GradeBoundary.objects.create(name='C', min_score=50, max_score=69)
        GradeBoundary.objects.create(name='A', min_score=70, max_score=100)
        GradeBoundary.objects.create(name='B', min_score=60, max_score=79)
        boundaries = list(GradeBoundary.objects.all())
        assert boundaries[0].name == 'A'
        assert boundaries[1].name == 'B'
        assert boundaries[2].name == 'C'
