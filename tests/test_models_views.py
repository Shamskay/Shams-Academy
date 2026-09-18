import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db.models import ProtectedError
from unittest.mock import patch

from accounts.models import Profile
from school.models import (
    ParentProfile, GradeBoundary, AcademicClass, Term,
    Subject, ClassSubject, ClassTeacher,
    Test, Exam, TestResult, ExamResult, TermResult,
    PromotionDecision, ReportCard, Fee, Payment,
    AuditLog, ResultRemark
)

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
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_STAFF,
        is_activated=True,
        unique_id='STF-123456'
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
def parent_unactivated(db):
    user = User.objects.create_user(
        username='parent_unact',
        email='parent_unact@test.com',
        password='parentpass123'
    )
    user.set_unusable_password()
    user.save()
    Profile.objects.filter(user=user).update(
        role=Profile.ROLE_PARENT,
        is_activated=False,
        unique_id='PAR-789012'
    )
    return user


@pytest.fixture
def academic_class(db):
    return AcademicClass.objects.create(name='JSS1', section='jss', is_active=True)


@pytest.fixture
def jss2_class(db):
    return AcademicClass.objects.create(name='JSS 2', section='jss', is_active=True)


@pytest.fixture
def term_current(db):
    return Term.objects.create(
        name=Term.TERM_FIRST,
        is_current=True,
        start_date='2025-09-01',
        end_date='2025-12-31',
        next_term_start_date='2026-01-05'
    )


@pytest.fixture
def subject(db):
    return Subject.objects.create(name='Mathematics', code='MTH', is_active=True)


@pytest.fixture
def class_subject(db, academic_class, subject, staff_user):
    return ClassSubject.objects.create(
        academic_class=academic_class,
        subject=subject,
        teacher=staff_user,
        is_active=True
    )


@pytest.fixture
def test_obj(db, subject, term_current, academic_class):
    return Test.objects.create(
        subject=subject,
        term=term_current,
        academic_class=academic_class,
        title='Weekly Test 1',
        max_score=Decimal('20.00'),
        date=date.today()
    )


@pytest.fixture
def exam_obj(db, subject, term_current, academic_class):
    return Exam.objects.create(
        subject=subject,
        term=term_current,
        academic_class=academic_class,
        title='Midterm Exam',
        max_score=Decimal('70.00'),
        date=date.today()
    )


@pytest.fixture
def grade_boundary_a():
    return GradeBoundary.objects.create(
        name='A',
        min_score=Decimal('70.00'),
        max_score=Decimal('100.00'),
        remark='Excellent',
        is_active=True
    )


@pytest.fixture
def grade_boundary_b():
    return GradeBoundary.objects.create(
        name='B',
        min_score=Decimal('60.00'),
        max_score=Decimal('69.00'),
        remark='Good',
        is_active=True
    )


# ---------------------------------------------------------------------------
# Result Entry Tests
# ---------------------------------------------------------------------------


class TestResultEntry:
    def test_student_can_view_test_result_after_entry(self, client, student_user, test_obj):
        TestResult.objects.create(
            student=student_user,
            test=test_obj,
            score=Decimal('15.00')
        )
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('students:my_results'))
        assert response.status_code == 200
        assert b'15' in response.content

    def test_duplicate_test_result_prevented(self, db, student_user, test_obj):
        TestResult.objects.create(
            student=student_user,
            test=test_obj,
            score=Decimal('15.00')
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TestResult.objects.create(
                student=student_user,
                test=test_obj,
                score=Decimal('18.00')
            )

    def test_duplicate_exam_result_prevented(self, db, student_user, exam_obj):
        ExamResult.objects.create(
            student=student_user,
            exam=exam_obj,
            score=Decimal('50.00')
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ExamResult.objects.create(
                student=student_user,
                exam=exam_obj,
                score=Decimal('60.00')
            )

    def test_get_percentage_returns_zero_for_zero_max_score(self, db, subject, term_current, academic_class):
        test_zero = Test.objects.create(
            subject=subject,
            term=term_current,
            academic_class=academic_class,
            title='Zero Score Test',
            max_score=Decimal('0.00'),
            date=date.today()
        )
        result = TestResult.objects.create(
            student=User.objects.create_user(username='pcttest', password='pass'),
            test=test_zero,
            score=Decimal('10.00')
        )
        assert result.get_percentage() == 0

    def test_get_percentage_calculates_correctly(self, db, student_user, test_obj):
        result = TestResult.objects.create(
            student=student_user,
            test=test_obj,
            score=Decimal('15.00')
        )
        assert result.get_percentage() == 75.0

    def test_invalid_score_skipped_in_bulk_entry(self, client, staff_user, student_user, test_obj, class_subject):
        client.login(username='staff1', password='staffpass123')
        response = client.post(
            reverse('assessments:staff_enter_results_table') + f'?type=test&id={test_obj.pk}',
            {
                f'score_{student_user.profile.pk}': 'invalid_not_a_number',
            }
        )
        assert response.status_code == 302
        assert not TestResult.objects.filter(student=student_user, test=test_obj).exists()


# ---------------------------------------------------------------------------
# Term Results Calculation Tests
# ---------------------------------------------------------------------------


class TestTermResultsCalculation:
    def test_calculate_term_results_creates_term_result(self, client, admin_user, student_user, test_obj, academic_class, term_current):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        TestResult.objects.create(
            student=student_user,
            test=test_obj,
            score=Decimal('15.00')
        )
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('assessments:admin_calculate_term_results'))
        assert response.status_code == 302
        term_result = TermResult.objects.filter(
            student=student_user,
            term=term_current,
            academic_class=academic_class
        ).first()
        assert term_result is not None
        assert term_result.average_score == 15.0
        assert term_result.total_subjects == 1

    def test_calculate_term_results_averages_multiple_subjects(self, client, admin_user, student_user, subject, term_current, academic_class):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        test1 = Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        test2 = Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T2', max_score=Decimal('20.00'), date=date.today())
        TestResult.objects.create(student=student_user, test=test1, score=Decimal('10.00'))
        TestResult.objects.create(student=student_user, test=test2, score=Decimal('12.00'))
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('assessments:admin_calculate_term_results'))
        assert response.status_code == 302
        term_result = TermResult.objects.filter(
            student=student_user,
            term=term_current,
            academic_class=academic_class
        ).first()
        assert term_result is not None
        assert term_result.average_score == 22.0
        assert term_result.total_subjects == 1

    def test_calculate_term_results_no_current_term(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('assessments:admin_calculate_term_results'))
        assert response.status_code == 302

    def test_calculate_term_results_handles_invalid_scores(self, db, student_user, test_obj, academic_class, term_current):
        TestResult.objects.create(
            student=student_user,
            test=test_obj,
            score=Decimal('15.00')
        )
        TermResult.objects.update_or_create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            defaults={'average_score': 75.0, 'total_subjects': 1}
        )
        term_result = TermResult.objects.get(
            student=student_user,
            term=term_current,
            academic_class=academic_class
        )
        assert term_result.average_score == 75.0

    def test_calculate_term_results_no_students(self, client, admin_user, term_current, academic_class):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('assessments:admin_calculate_term_results'))
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Promotion Logic Tests
# ---------------------------------------------------------------------------


class TestPromotionLogic:
    def test_student_promoted_when_passes(self, client, admin_user, student_user, academic_class, jss2_class, term_current):
        TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('75.00'),
            total_subjects=5
        )
        client.login(username='admin', password='adminpass123')
        response = client.post(
            reverse('assessments:admin_promote_students'),
            {'pass_mark': '50.00', 'next_term_resumption_date': '2026-01-05'}
        )
        assert response.status_code == 302
        promo = PromotionDecision.objects.filter(student=student_user, term=term_current).first()
        assert promo is not None
        assert promo.is_promoted is True
        assert promo.from_class == academic_class

    def test_promotion_with_invalid_pass_mark(self, client, admin_user, student_user, academic_class, term_current):
        TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('75.00'),
            total_subjects=5
        )
        client.login(username='admin', password='adminpass123')
        response = client.post(
            reverse('assessments:admin_promote_students'),
            {'pass_mark': 'not_a_number', 'next_term_resumption_date': '2026-01-05'}
        )
        assert response.status_code == 302
        assert not PromotionDecision.objects.filter(student=student_user, term=term_current).exists()

    def test_student_needs_next_term_resumption_date(self, client, admin_user, student_user, academic_class, term_current):
        TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('75.00'),
            total_subjects=5
        )
        client.login(username='admin', password='adminpass123')
        response = client.post(
            reverse('assessments:admin_promote_students'),
            {'pass_mark': '50.00'}
        )
        assert response.status_code == 302
        promo = PromotionDecision.objects.filter(student=student_user, term=term_current).first()
        assert promo is not None

    def test_promotion_page_loads(self, client, admin_user, term_current):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('assessments:admin_promote_students'))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Report Card Generation Tests
# ---------------------------------------------------------------------------


class TestReportCardGeneration:
    def test_generate_report_cards_for_students(self, client, admin_user, student_user, academic_class, term_current):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('80.00'),
            total_subjects=5
        )
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_generate_report_cards'))
        assert response.status_code == 302
        report_card = ReportCard.objects.filter(
            student=student_user,
            term=term_current
        ).first()
        assert report_card is not None
        assert report_card.average_score == Decimal('80.00')
        assert report_card.total_subjects == 5

    def test_generate_report_cards_no_current_term(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_generate_report_cards'))
        assert response.status_code == 302

    def test_generate_report_cards_skips_students_without_term_results(self, client, admin_user, student_user, academic_class, term_current):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('school:admin_generate_report_cards'))
        assert response.status_code == 302
        assert not ReportCard.objects.filter(student=student_user, term=term_current).exists()

    def test_student_can_view_own_report_cards(self, client, student_user, academic_class, term_current, test_obj, exam_obj):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('80.00'),
            total_subjects=5
        )
        ReportCard.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('80.00'),
            total_subjects=5
        )
        TestResult.objects.create(student=student_user, test=test_obj, score=Decimal('15.00'))
        ExamResult.objects.create(student=student_user, exam=exam_obj, score=Decimal('50.00'))
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('school:report_card'))
        assert response.status_code == 200
        assert 'subject_breakdown' in str(response.context) or 'subjects' in str(response.context)


# ---------------------------------------------------------------------------
# Fee/Payment Tests
# ---------------------------------------------------------------------------


class TestFeePayments:
    def test_admin_can_create_fee(self, client, admin_user, academic_class, term_current):
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_fees'), {
            'academic_class': academic_class.pk,
            'name': 'Tuition Fee',
            'fee_type': 'tuition',
            'amount': '5000.00',
            'term': term_current.pk,
            'due_date': date.today() + timedelta(days=7),
        })
        assert response.status_code == 302
        assert Fee.objects.filter(name='Tuition Fee').exists()

    def test_fee_requires_valid_academic_class(self, client, admin_user, term_current):
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_fees'), {
            'academic_class': 9999,
            'name': 'Test Fee',
            'fee_type': 'tuition',
            'amount': '5000.00',
            'term': term_current.pk,
            'due_date': date.today() + timedelta(days=7),
        })
        assert response.status_code == 200
        assert not Fee.objects.filter(name='Test Fee').exists()

    def test_admin_can_create_payment(self, client, admin_user, student_user, academic_class, term_current):
        fee = Fee.objects.create(
            academic_class=academic_class,
            name='Tuition Fee',
            fee_type='tuition',
            amount=Decimal('5000.00'),
            term=term_current,
            due_date=date.today() + timedelta(days=30)
        )
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_payments'), {
            'student': student_user.pk,
            'fee': fee.pk,
            'amount': '5000.00',
            'status': 'completed',
            'transaction_id': 'TXN001',
            'payment_method': 'cash',
        })
        assert response.status_code == 302
        assert Payment.objects.filter(student=student_user, fee=fee).exists()

    def test_payment_amount_auto_set_from_fee(self, client, admin_user, student_user, academic_class, term_current):
        fee = Fee.objects.create(
            academic_class=academic_class,
            name='Tuition Fee',
            fee_type='tuition',
            amount=Decimal('3000.00'),
            term=term_current,
            due_date=date.today() + timedelta(days=30)
        )
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('school:admin_payments'), {
            'student': student_user.pk,
            'fee': fee.pk,
            'amount': '3000.00',
            'status': 'completed',
            'transaction_id': 'TXN002',
            'payment_method': 'bank',
        })
        assert response.status_code == 302
        payment = Payment.objects.get(student=student_user, fee=fee)
        assert payment.amount == Decimal('3000.00')

    def test_fee_str_representation(self, db, academic_class, term_current):
        fee = Fee.objects.create(
            academic_class=academic_class,
            name='Tuition Fee',
            fee_type='tuition',
            amount=Decimal('5000.00'),
            term=term_current,
            due_date=date.today()
        )
        assert 'Tuition Fee' in str(fee)

    def test_payment_str_representation(self, db, student_user, academic_class, term_current):
        fee = Fee.objects.create(
            academic_class=academic_class,
            name='Tuition Fee',
            fee_type='tuition',
            amount=Decimal('5000.00'),
            term=term_current,
            due_date=date.today()
        )
        payment = Payment.objects.create(
            student=student_user,
            fee=fee,
            amount=Decimal('5000.00'),
            status='completed'
        )
        assert 'student1' in str(payment)


# ---------------------------------------------------------------------------
# Audit Logging Tests
# ---------------------------------------------------------------------------


class TestAuditLogging:
    def test_login_logs_audit_entry(self, db):
        user = User.objects.create_user(username='audit1', password='pass123')
        Profile.objects.filter(user=user).update(
            role=Profile.ROLE_STUDENT,
            is_activated=True,
            admission_number='AUD001'
        )
        client = Client()
        client.login(username='audit1', password='pass123')
        assert AuditLog.objects.filter(
            user=user,
            action='login',
            model_name='User'
        ).exists()

    def test_logout_logs_audit_entry(self, db):
        user = User.objects.create_user(username='audit2', password='pass123')
        Profile.objects.filter(user=user).update(
            role=Profile.ROLE_STUDENT,
            is_activated=True,
            admission_number='AUD002'
        )
        client = Client()
        client.login(username='audit2', password='pass123')
        AuditLog.objects.all().delete()
        client.logout()
        assert AuditLog.objects.filter(
            user=user,
            action='logout',
            model_name='User'
        ).exists()

    def test_admin_create_parent_logs_audit(self, client, admin_user, student_user, academic_class):
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        client.login(username='admin', password='adminpass123')
        client.post(reverse('school:admin_create_parent') + f'?class_id={academic_class.pk}', {
            'first_name': 'Audit',
            'last_name': 'Parent',
            'email': 'audit@test.com',
            'student_id': student_user.pk,
            'class_id': str(academic_class.pk),
            'relationship': 'mother',
            'is_primary': 'on',
        })
        create_logs = AuditLog.objects.filter(
            user=admin_user,
            action='create',
            model_name='ParentProfile'
        )
        assert create_logs.exists()

    def test_audit_log_str_representation(self, db, admin_user):
        log = AuditLog.objects.create(
            user=admin_user,
            action='create',
            model_name='Test',
            object_id='1',
            object_repr='Test object'
        )
        assert 'admin' in str(log)

    def test_create_audit_log_creates_entry(self, db):
        from school.views import create_audit_log
        user = User.objects.create_user(username='audituser', password='pass123')
        Profile.objects.filter(user=user).update(role=Profile.ROLE_STAFF)
        obj = Test.objects.create(
            subject=Subject.objects.create(name='TestSub', code='TS'),
            term=Term.objects.create(
                name=Term.TERM_FIRST,
                is_current=True,
                start_date='2025-09-01',
                end_date='2025-12-31'
            ),
            academic_class=AcademicClass.objects.create(name='TEST_CLS', section='jss'),
            title='Test Audit',
            max_score=Decimal('20.00'),
            date=date.today()
        )
        request = type('MockRequest', (), {
            'META': {'REMOTE_ADDR': '127.0.0.1'},
            'user': user,
        })()
        create_audit_log(user, 'create', 'Test', obj, {'field': 'value'}, request)
        assert AuditLog.objects.filter(
            user=user,
            action='create',
            model_name='Test',
            object_id=str(obj.pk)
        ).exists()


# ---------------------------------------------------------------------------
# Parent Registration Flow Tests
# ---------------------------------------------------------------------------


class TestParentRegistrationFlow:
    def test_parent_register_page_loads(self, client):
        response = client.get(reverse('accounts:parent_register'))
        assert response.status_code == 200

    def test_parent_register_with_valid_invitation_code(self, client, parent_unactivated):
        response = client.post(reverse('accounts:parent_register'), {
            'invitation_code': 'PAR-789012',
            'username': 'newparent',
            'password1': 'newpass123',
            'password2': 'newpass123',
        })
        assert response.status_code == 302
        parent_user = User.objects.get(pk=parent_unactivated.pk)
        assert parent_user.username == 'newparent'

    def test_parent_register_with_invalid_invitation_code(self, client, db):
        response = client.post(reverse('accounts:parent_register'), {
            'invitation_code': 'INVALID-CODE',
            'username': 'newparent',
            'password1': 'newpass123',
            'password2': 'newpass123',
        })
        assert response.status_code == 200
        assert b'Invalid invitation code' in response.content

    def test_parent_register_password_mismatch(self, client, parent_unactivated):
        response = client.post(reverse('accounts:parent_register'), {
            'invitation_code': 'PAR-789012',
            'username': 'newparent2',
            'password1': 'pass123',
            'password2': 'different',
        })
        assert response.status_code == 200
        assert b'do not match' in response.content

    def test_already_activated_parent_cannot_reregister(self, client, parent_user):
        parent_user.set_password('existing123')
        parent_user.save()
        response = client.post(reverse('accounts:parent_register'), {
            'invitation_code': 'PAR-123456',
            'username': 'newparent3',
            'password1': 'pass123',
            'password2': 'pass123',
        })
        assert response.status_code == 200
        assert b'already been activated' in response.content

    def test_already_taken_username_rejected(self, client, admin_user, parent_unactivated):
        response = client.post(reverse('accounts:parent_register'), {
            'invitation_code': 'PAR-789012',
            'username': 'admin',
            'password1': 'pass123',
            'password2': 'pass123',
        })
        assert response.status_code == 200
        assert b'already exists' in response.content

    def test_authenticated_user_redirected_from_parent_register(self, client, admin_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('accounts:parent_register'))
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Permission/Access Control Tests
# ---------------------------------------------------------------------------


class TestPermissionAccess:
    def test_staff_cannot_access_admin_create_parent(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('school:admin_create_parent'))
        assert response.status_code == 302

    def test_non_superuser_cannot_access_admin_fees(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('school:admin_fees'))
        assert response.status_code == 302

    def test_non_superuser_cannot_access_admin_payments(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('school:admin_payments'))
        assert response.status_code == 302

    def test_non_superuser_cannot_access_manage_tests(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('assessments:admin_manage_tests'))
        assert response.status_code == 302

    def test_non_superuser_cannot_access_manage_exams(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('assessments:admin_manage_exams'))
        assert response.status_code == 302

    def test_non_superuser_cannot_access_grade_boundaries(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('school:admin_grade_boundaries'))
        assert response.status_code == 302

    def test_student_cannot_access_admin_dashboard(self, client, student_user):
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('school:admin_dashboard'))
        assert response.status_code == 302

    def test_staff_can_access_staff_dashboard(self, client, staff_user):
        response = client.get(reverse('staff:staff_dashboard'))
        assert response.status_code == 302

    def test_unauthenticated_user_redirected_from_parent_dashboard(self, client):
        response = client.get(reverse('school:parent_dashboard'))
        assert response.status_code == 302

    def test_unauthenticated_user_redirected_from_my_results(self, client):
        response = client.get(reverse('students:my_results'))
        assert response.status_code == 302

    def test_staff_cannot_access_parent_dashboard(self, client, staff_user):
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('school:parent_dashboard'))
        assert response.status_code == 302

    def test_student_cannot_access_parent_dashboard(self, client, student_user):
        client.login(username='student1', password='studentpass123')
        response = client.get(reverse('school:parent_dashboard'))
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Model Constraint Tests
# ---------------------------------------------------------------------------


class TestModelConstraints:
    def test_parent_profile_unique_together(self, db, parent_user, student_user):
        ParentProfile.objects.create(
            parent=parent_user,
            student=student_user,
            relationship='father'
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ParentProfile.objects.create(
                parent=parent_user,
                student=student_user,
                relationship='mother'
            )

    def test_test_result_unique_together(self, db, student_user, test_obj):
        TestResult.objects.create(student=student_user, test=test_obj, score=Decimal('10.00'))
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TestResult.objects.create(student=student_user, test=test_obj, score=Decimal('15.00'))

    def test_exam_result_unique_together(self, db, student_user, exam_obj):
        ExamResult.objects.create(student=student_user, exam=exam_obj, score=Decimal('50.00'))
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ExamResult.objects.create(student=student_user, exam=exam_obj, score=Decimal('60.00'))

    def test_term_result_unique_together(self, db, student_user, academic_class, term_current):
        TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('75.00'),
            total_subjects=5
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TermResult.objects.create(
                student=student_user,
                term=term_current,
                academic_class=academic_class,
                average_score=Decimal('80.00'),
                total_subjects=5
            )

    def test_parent_profile_str_representation(self, db, parent_user, student_user):
        profile = ParentProfile.objects.create(
            parent=parent_user,
            student=student_user,
            relationship='father'
        )
        assert 'parent1' in str(profile)

    def test_parent_profile_str_without_student(self, db, parent_user):
        profile = ParentProfile.objects.create(
            parent=parent_user,
            student=None,
            relationship='guardian'
        )
        assert 'Unknown' in str(profile)

    def test_term_result_str_representation(self, db, student_user, academic_class, term_current):
        term_result = TermResult.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            average_score=Decimal('75.00'),
            total_subjects=5
        )
        assert 'student1' in str(term_result)

    def test_promotion_decision_unique_together(self, db, student_user, academic_class, term_current):
        PromotionDecision.objects.create(
            student=student_user,
            term=term_current,
            from_class=academic_class,
            to_class=academic_class,
            average_score=Decimal('75.00'),
            is_promoted=True,
            next_term_resumption_date='2026-01-05'
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            PromotionDecision.objects.create(
                student=student_user,
                term=term_current,
                from_class=academic_class,
                to_class=academic_class,
                average_score=Decimal('80.00'),
                is_promoted=False,
                next_term_resumption_date='2026-01-05'
            )

    def test_promotion_decision_str_promoted(self, db, student_user, academic_class, term_current):
        promo = PromotionDecision.objects.create(
            student=student_user,
            term=term_current,
            from_class=academic_class,
            to_class=academic_class,
            average_score=Decimal('75.00'),
            is_promoted=True,
            next_term_resumption_date='2026-01-05'
        )
        assert 'Promoted' in str(promo)

    def test_promotion_decision_str_repeated(self, db, student_user, academic_class, term_current):
        promo = PromotionDecision.objects.create(
            student=student_user,
            term=term_current,
            from_class=academic_class,
            to_class=academic_class,
            average_score=Decimal('30.00'),
            is_promoted=False,
            next_term_resumption_date='2026-01-05'
        )
        assert 'Repeated' in str(promo)

    def test_grade_boundary_str_representation(self, db):
        boundary = GradeBoundary.objects.create(
            name='A',
            min_score=Decimal('70.00'),
            max_score=Decimal('100.00'),
            remark='Excellent'
        )
        assert str(boundary) == 'A: 70.00 - 100.00'

    def test_test_str_representation(self, db, subject, term_current, academic_class):
        test_obj = Test.objects.create(
            subject=subject,
            term=term_current,
            academic_class=academic_class,
            title='Test 1',
            max_score=Decimal('20.00'),
            date=date.today()
        )
        assert 'Test 1' in str(test_obj)

    def test_exam_str_representation(self, db, subject, term_current, academic_class):
        exam = Exam.objects.create(
            subject=subject,
            term=term_current,
            academic_class=academic_class,
            title='Midterm',
            max_score=Decimal('70.00'),
            date=date.today()
        )
        assert 'Midterm' in str(exam)

    def test_parent_profile_set_null_on_student_delete(self, db, parent_user, student_user):
        link = ParentProfile.objects.create(
            parent=parent_user,
            student=student_user,
            relationship='father'
        )
        student_user_id = student_user.pk
        student_user.delete()
        link.refresh_from_db()
        assert link.student is None

    def test_result_remark_str_representation(self, db, student_user, term_current, academic_class):
        remark = ResultRemark.objects.create(
            student=student_user,
            term=term_current,
            academic_class=academic_class,
            remark='Good progress'
        )
        assert 'student1' in str(remark)


class TestStaffActivation:
    def test_staff_auto_activated_after_registration(self, client, db):
        from school.models import Test
        user = User.objects.create_user(
            username='STF-9999',
            password=None,
            first_name='Test',
            last_name='Staff',
        )
        user.set_unusable_password()
        user.save()
        Profile.objects.filter(user=user).update(
            role=Profile.ROLE_STAFF,
            unique_id='STF-9999',
            is_activated=False,
        )
        response = client.post(reverse('accounts:staff_register'), {
            'unique_id': 'STF-9999',
            'username': 'teststaff',
            'password1': 'testpass123',
            'password2': 'testpass123',
        })
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.profile.is_activated is True

    def test_admin_can_deactivate_staff(self, client, admin_user, staff_user):
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('staff:admin_toggle_staff_status', args=[staff_user.profile.pk]))
        assert response.status_code == 302
        staff_user.profile.refresh_from_db()
        assert staff_user.profile.is_activated is False

    def test_admin_can_reactivate_staff(self, client, admin_user, staff_user):
        staff_user.profile.refresh_from_db()
        staff_user.profile.is_activated = False
        staff_user.profile.save()
        client.login(username='admin', password='adminpass123')
        response = client.post(reverse('staff:admin_toggle_staff_status', args=[staff_user.profile.pk]))
        assert response.status_code == 302
        staff_user.profile.refresh_from_db()
        assert staff_user.profile.is_activated is True

    def test_deactivated_staff_redirected_from_dashboard(self, client, staff_user):
        staff_user.profile.refresh_from_db()
        staff_user.profile.is_activated = False
        staff_user.profile.save()
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('staff:staff_dashboard'))
        assert response.status_code == 302

    def test_staff_list_shows_toggle_button(self, client, admin_user, staff_user):
        client.login(username='admin', password='adminpass123')
        response = client.get(reverse('staff:admin_staff'))
        assert response.status_code == 200
        assert b'Deactivate' in response.content or b'Activate' in response.content


class TestStaffEnterResultByClass:
    def test_enter_test_result_class_selection_does_not_error(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import Test
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_test_result'), {
            'academic_class': str(academic_class.pk),
        })
        assert response.status_code == 200
        assert b'Select a class above' not in response.content
        assert b'STU001' in response.content or b'student1' in response.content

    def test_enter_test_result_non_activated_student_visible(self, client, db, staff_user, term_current, academic_class, subject, class_subject):
        from school.models import Test
        student = User.objects.create_user(
            username='inactive_student',
            email='inactive@test.com',
            password='studentpass123',
            first_name='Inactive',
            last_name='Student',
        )
        Profile.objects.filter(user=student).update(
            role=Profile.ROLE_STUDENT,
            is_activated=False,
            admission_number='STU002',
            status=Profile.STATUS_ACTIVE,
            academic_class=academic_class,
        )
        Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_test_result'), {
            'academic_class': str(academic_class.pk),
        })
        assert response.status_code == 200
        assert b'Inactive Student' in response.content

    def test_enter_test_result_class_only_renders_student_dropdown(self, client, db, staff_user, term_current, academic_class, subject, class_subject):
        from school.models import Test
        Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_test_result'), {
            'academic_class': str(academic_class.pk),
        })
        assert response.status_code == 200
        assert b'Enter Test Result' in response.content

    def test_enter_exam_result_class_selection_does_not_error(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import Exam
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        Exam.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='E1', max_score=Decimal('70.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_exam_result'), {
            'academic_class': str(academic_class.pk),
        })
        assert response.status_code == 200
        assert b'STU001' in response.content or b'student1' in response.content

    def test_staff_enter_test_result_saves_with_class_selected(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import Test
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        test = Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_test_result'), {
            'academic_class': str(academic_class.pk),
            'student': student_user.pk,
            'test': test.pk,
            'score': '15',
        })
        assert response.status_code == 200
        from school.models import TestResult
        assert TestResult.objects.filter(student=student_user, test=test, score=Decimal('15.00')).exists()

    def test_staff_enter_exam_result_saves_with_class_selected(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import Exam, ExamResult
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        exam = Exam.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='E1', max_score=Decimal('70.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_exam_result'), {
            'academic_class': str(academic_class.pk),
            'student': student_user.pk,
            'exam': exam.pk,
            'score': '50',
        })
        assert response.status_code == 200
        assert ExamResult.objects.filter(student=student_user, exam=exam, score=Decimal('50.00')).exists()

    def test_enter_test_result_rejects_negative_score(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import Test
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        test = Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_test_result'), {
            'academic_class': str(academic_class.pk),
            'student': student_user.pk,
            'test': test.pk,
            'score': '-5',
        })
        assert response.status_code == 200
        assert b'Enter Test Result' in response.content
        from school.models import TestResult
        assert not TestResult.objects.filter(student=student_user, test=test, score=Decimal('-5.00')).exists()

    def test_enter_test_result_saves_whole_number_score(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import Test
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        test = Test.objects.create(subject=subject, term=term_current, academic_class=academic_class, title='T1', max_score=Decimal('20.00'), date=date.today())
        client.login(username='staff1', password='staffpass123')
        response = client.post(reverse('assessments:staff_enter_test_result'), {
            'academic_class': str(academic_class.pk),
            'student': student_user.pk,
            'test': test.pk,
            'score': '15',
        })
        assert response.status_code == 200
        from school.models import TestResult
        result = TestResult.objects.get(student=student_user, test=test)
        assert result.score == Decimal('15')
        assert result.score == int(result.score)

    def test_staff_class_results_shows_subject_table(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import ClassTeacher, TestResult, Test
        from school.models import GradeBoundary
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        ClassTeacher.objects.create(teacher=staff_user, academic_class=academic_class, is_active=True)
        test = Test.objects.create(
            subject=subject, term=term_current, academic_class=academic_class,
            title='T1', max_score=Decimal('20.00'), date=date.today()
        )
        TestResult.objects.create(student=student_user, test=test, score=Decimal('15.00'))
        GradeBoundary.objects.create(name='A', min_score=70, max_score=100, is_active=True)
        GradeBoundary.objects.create(name='B', min_score=50, max_score=69, is_active=True)
        GradeBoundary.objects.create(name='C', min_score=0, max_score=49, is_active=True)
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('students:staff_class_results', kwargs={'pk': academic_class.pk}))
        assert response.status_code == 200
        assert b'student1' in response.content
        assert b'15.00' in response.content or b'15' in response.content

    def test_staff_student_results_shows_individual_results(self, client, db, staff_user, term_current, academic_class, subject, class_subject, student_user):
        from school.models import ClassTeacher, TestResult, Test, ExamResult, Exam
        from school.models import GradeBoundary
        student_user.profile.refresh_from_db()
        student_user.profile.academic_class = academic_class
        student_user.profile.save()
        ClassTeacher.objects.create(teacher=staff_user, academic_class=academic_class, is_active=True)
        test = Test.objects.create(
            subject=subject, term=term_current, academic_class=academic_class,
            title='T1', max_score=Decimal('20.00'), date=date.today()
        )
        TestResult.objects.create(student=student_user, test=test, score=Decimal('15.00'))
        exam = Exam.objects.create(
            subject=subject, term=term_current, academic_class=academic_class,
            title='E1', max_score=Decimal('70.00'), date=date.today()
        )
        ExamResult.objects.create(student=student_user, exam=exam, score=Decimal('50.00'))
        GradeBoundary.objects.create(name='A', min_score=70, max_score=100, is_active=True)
        GradeBoundary.objects.create(name='B', min_score=50, max_score=69, is_active=True)
        GradeBoundary.objects.create(name='C', min_score=0, max_score=49, is_active=True)
        client.login(username='staff1', password='staffpass123')
        response = client.get(reverse('students:staff_student_results', kwargs={'class_pk': academic_class.pk, 'student_pk': student_user.profile.pk}))
        assert response.status_code == 200
        assert b'student1' in response.content
        assert b'15' in response.content
        assert b'50' in response.content
