from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone


class Term(models.Model):
    TERM_FIRST = 'first'
    TERM_SECOND = 'second'
    TERM_THIRD = 'third'
    TERM_CHOICES = [
        (TERM_FIRST, 'First Term'),
        (TERM_SECOND, 'Second Term'),
        (TERM_THIRD, 'Third Term'),
    ]

    name = models.CharField(max_length=20, choices=TERM_CHOICES, unique=True)
    is_current = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()
    next_term_start_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Term'
        verbose_name_plural = 'Terms'

    def __str__(self):
        return self.get_name_display()


class AcademicClass(models.Model):
    SECTION_JSS = 'jss'
    SECTION_SS = 'ss'
    SECTION_CHOICES = [
        (SECTION_JSS, 'Junior Secondary'),
        (SECTION_SS, 'Senior Secondary'),
    ]

    name = models.CharField(max_length=50, unique=True, help_text="e.g. JSS1, SS2")
    section = models.CharField(max_length=5, choices=SECTION_CHOICES)
    next_class = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='previous_class',
        help_text="The class students are promoted to after this class. Leave blank for final class (SS3)."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['section', 'name']
        verbose_name = 'Class'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.name

    def is_final_class(self):
        """Returns True if this is the final class (no next_class defined)."""
        return self.next_class is None


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_core = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class ClassSubject(models.Model):
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='class_subjects'
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='class_subjects'
    )
    teacher = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='teaching_assignments'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('academic_class', 'subject')
        ordering = ['academic_class__name', 'subject__code']
        verbose_name = 'Class Subject'
        verbose_name_plural = 'Class Subjects'

    def __str__(self):
        return f'{self.academic_class.name} - {self.subject.code}'


class ClassTeacher(models.Model):
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='class_teachers'
    )
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='class_teacher_assignments'
    )
    is_active = models.BooleanField(default=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['academic_class__name']
        verbose_name = 'Class Teacher'
        verbose_name_plural = 'Class Teachers'
        constraints = [
            models.UniqueConstraint(fields=['academic_class'], name='unique_class_teacher')
        ]

    def __str__(self):
        return f'{self.academic_class.name} - {self.teacher.get_full_name() or self.teacher.username}'


class StudyMaterial(models.Model):
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='materials'
    )
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.SET_NULL, null=True, blank=True, related_name='materials'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='materials'
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='uploaded_materials'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.academic_class:
            return f'{self.title} ({self.academic_class.name} - {self.subject.code})'
        return f'{self.title} ({self.subject.code})'


class Test(models.Model):
    __test__ = False
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='tests'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='tests'
    )
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='tests'
    )
    title = models.CharField(max_length=200)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=20.00)
    date = models.DateField()
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'Test: {self.title} ({self.subject.code}) - {self.academic_class.name}'


class Exam(models.Model):
    __test__ = False
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name='exams'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='exams'
    )
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='exams'
    )
    title = models.CharField(max_length=200)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=70.00)
    date = models.DateField()
    instructions = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'Exam: {self.title} ({self.subject.code}) - {self.academic_class.name}'


class TestResult(models.Model):
    __test__ = False
    ENTERED_BY_STUDENT = 'student'
    ENTERED_BY_TEACHER = 'teacher'
    ENTERED_BY_CHOICES = [
        (ENTERED_BY_STUDENT, 'Student'),
        (ENTERED_BY_TEACHER, 'Teacher'),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='test_results'
    )
    test = models.ForeignKey(
        Test, on_delete=models.CASCADE, related_name='results'
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    entered_by = models.CharField(max_length=10, choices=ENTERED_BY_CHOICES, default=ENTERED_BY_TEACHER)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'test')
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.student.username} - {self.test.title}: {self.score}'

    def get_percentage(self):
        if self.test.max_score > 0:
            return round(max(0, (float(self.score) / float(self.test.max_score)) * 100), 2)
        return 0


class ExamResult(models.Model):
    __test__ = False
    ENTERED_BY_STUDENT = 'student'
    ENTERED_BY_TEACHER = 'teacher'
    ENTERED_BY_CHOICES = [
        (ENTERED_BY_STUDENT, 'Student'),
        (ENTERED_BY_TEACHER, 'Teacher'),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='exam_results'
    )
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='results'
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)
    entered_by = models.CharField(max_length=10, choices=ENTERED_BY_CHOICES, default=ENTERED_BY_TEACHER)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'exam')
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.student.username} - {self.exam.title}: {self.score}'

    def get_percentage(self):
        if self.exam.max_score > 0:
            return round(max(0, (float(self.score) / float(self.exam.max_score)) * 100), 2)
        return 0


class Question(models.Model):
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('true_false', 'True/False'),
    ]

    test = models.ForeignKey(
        Test, on_delete=models.CASCADE, related_name='questions', null=True, blank=True
    )
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='questions', null=True, blank=True
    )
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='mcq')
    text = models.TextField()
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        assessment = self.test or self.exam
        return f'Q{self.order}: {self.text[:50]}... ({assessment})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.test and not self.exam:
            raise ValidationError('Question must belong to either a Test or an Exam.')
        if self.test and self.exam:
            raise ValidationError('Question cannot belong to both a Test and an Exam.')

    def get_correct_options(self):
        return self.options.filter(is_correct=True)


class Option(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='options'
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.text[:50]}... ({"Correct" if self.is_correct else "Incorrect"})'


class TermResult(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='term_results'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='term_results'
    )
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='term_results'
    )
    average_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_subjects = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'term')
        ordering = ['-calculated_at']

    def __str__(self):
        return f'{self.student.username} - {self.term.name}: {self.average_score}'


class PromotionDecision(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='promotion_decisions'
    )
    from_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='promoted_from'
    )
    to_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='promoted_to'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='promotion_decisions'
    )
    average_score = models.DecimalField(max_digits=6, decimal_places=2)
    is_promoted = models.BooleanField()
    remarks = models.TextField(blank=True)
    next_term_resumption_date = models.DateField()
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'term')
        ordering = ['-decided_at']

    def __str__(self):
        status = 'Promoted' if self.is_promoted else 'Repeated'
        return f'{self.student.username} - {self.term.name}: {status}'


class GradeBoundary(models.Model):
    name = models.CharField(max_length=5, help_text='e.g. A, B, C, D, E, F')
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    remark = models.CharField(max_length=100, blank=True, help_text='e.g. Excellent, Good, Average, Poor')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-min_score']
        verbose_name = 'Grade Boundary'
        verbose_name_plural = 'Grade Boundaries'

    def __str__(self):
        return f'{self.name}: {self.min_score} - {self.max_score}'


class ResultRemark(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='result_remarks'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='result_remarks'
    )
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='result_remarks'
    )
    remark = models.TextField()
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='given_remarks'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Result Remark'
        verbose_name_plural = 'Result Remarks'

    def __str__(self):
        return f'Remark for {self.student.username} - {self.term.name}'


class ReportCard(models.Model):
    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='report_cards'
    )
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='report_cards'
    )
    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='report_cards'
    )
    average_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    total_subjects = models.PositiveIntegerField(default=0)
    class_teacher_remark = models.TextField(blank=True)
    principal_remark = models.TextField(blank=True)
    next_term_resumption_date = models.DateField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-generated_at']
        verbose_name = 'Report Card'
        verbose_name_plural = 'Report Cards'

    def __str__(self):
        return f'Report Card: {self.student.username} - {self.term.name}'


class ParentProfile(models.Model):
    parent = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='children_profiles'
    )
    student = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='parent_profiles'
    )
    relationship = models.CharField(max_length=20, choices=[
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('guardian', 'Guardian'),
    ])
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('parent', 'student')
        ordering = ['-is_primary', 'relationship']
        verbose_name = 'Parent Profile'
        verbose_name_plural = 'Parent Profiles'

    def __str__(self):
        student_name = self.student.username if self.student else 'Unknown'
        return f'{self.parent.get_full_name() or self.parent.username} - {self.relationship} of {student_name}'


class SchoolEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('holiday', 'Holiday'),
        ('exam', 'Examination'),
        ('meeting', 'Parent Meeting'),
        ('sports', 'Sports'),
        ('cultural', 'Cultural'),
        ('academic', 'Academic'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='other')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'School Event'
        verbose_name_plural = 'School Events'

    def __str__(self):
        return f'{self.title} ({self.start_date})'


class Fee(models.Model):
    FEE_TYPE_CHOICES = [
        ('tuition', 'Tuition'),
        ('exam', 'Examination'),
        ('sports', 'Sports'),
        ('other', 'Other'),
    ]

    academic_class = models.ForeignKey(
        AcademicClass, on_delete=models.CASCADE, related_name='fees'
    )
    name = models.CharField(max_length=200, blank=True, null=True, help_text="Auto-generated if left blank")
    fee_type = models.CharField(max_length=20, choices=FEE_TYPE_CHOICES, default='tuition')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    term = models.ForeignKey(
        Term, on_delete=models.CASCADE, related_name='fees'
    )
    due_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fee'
        verbose_name_plural = 'Fees'

    def __str__(self):
        return f'{self.name} - {self.academic_class.name} ({self.term.name})'


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    student = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='payments'
    )
    fee = models.ForeignKey(
        Fee, on_delete=models.CASCADE, related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f'{self.student.username} - {self.fee.name}: {self.amount}'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f'{self.user} - {self.action} - {self.model_name} ({self.timestamp})'
