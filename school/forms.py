from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import Profile
from .models import (
    Term, AcademicClass, Subject, ClassSubject, ClassTeacher,
    Test, Exam, TestResult, ExamResult,
    PromotionDecision, GradeBoundary, ResultRemark, ReportCard,
    ParentProfile, SchoolEvent, Fee, Payment
)

class TermForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class AcademicClassForm(forms.ModelForm):
    class Meta:
        model = AcademicClass
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class ClassSubjectForm(forms.ModelForm):
    class Meta:
        model = ClassSubject
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(
            Q(profile__role=Profile.ROLE_STAFF) | Q(profile__isnull=True) | Q(is_superuser=True)
        ).distinct()
        self.fields['teacher'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username}"
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class ClassTeacherForm(forms.ModelForm):
    class Meta:
        model = ClassTeacher
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(
            Q(profile__role=Profile.ROLE_STAFF, profile__is_activated=True) | Q(profile__isnull=True) | Q(is_superuser=True)
        ).distinct()
        self.fields['teacher'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username}"
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})



class TestForm(forms.ModelForm):
    max_score = forms.IntegerField(
        min_value=1,
        label='Max Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'})
    )

    class Meta:
        model = Test
        fields = ['subject', 'term', 'academic_class', 'title', 'max_score', 'date', 'instructions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class ExamForm(forms.ModelForm):
    max_score = forms.IntegerField(
        min_value=1,
        label='Max Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'})
    )

    class Meta:
        model = Exam
        fields = ['subject', 'term', 'academic_class', 'title', 'max_score', 'date', 'instructions']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class TeacherTestForm(forms.ModelForm):
    max_score = forms.IntegerField(
        min_value=1,
        label='Max Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'})
    )

    class Meta:
        model = Test
        fields = ['subject', 'term', 'academic_class', 'title', 'max_score', 'date', 'instructions']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            teaching_assignments = ClassSubject.objects.filter(
                teacher=user, is_active=True
            ).select_related('subject', 'academic_class')
            subjects = Subject.objects.filter(
                pk__in=teaching_assignments.values_list('subject_id', flat=True)
            )
            classes = AcademicClass.objects.filter(
                pk__in=teaching_assignments.values_list('academic_class_id', flat=True)
            )
            self.fields['subject'].queryset = subjects
            self.fields['academic_class'].queryset = classes
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class TeacherExamForm(forms.ModelForm):
    max_score = forms.IntegerField(
        min_value=1,
        label='Max Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'step': '1'})
    )

    class Meta:
        model = Exam
        fields = ['subject', 'term', 'academic_class', 'title', 'max_score', 'date', 'instructions']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            teaching_assignments = ClassSubject.objects.filter(
                teacher=user, is_active=True
            ).select_related('subject', 'academic_class')
            subjects = Subject.objects.filter(
                pk__in=teaching_assignments.values_list('subject_id', flat=True)
            )
            classes = AcademicClass.objects.filter(
                pk__in=teaching_assignments.values_list('academic_class_id', flat=True)
            )
            self.fields['subject'].queryset = subjects
            self.fields['academic_class'].queryset = classes
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class TestResultForm(forms.ModelForm):
    academic_class = forms.ChoiceField(
        choices=[],
        required=False,
        label='Class',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_result_class'})
    )
    score = forms.IntegerField(
        min_value=0,
        label='Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'})
    )

    class Meta:
        model = TestResult
        fields = ['student', 'test', 'score']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            if user.is_superuser:
                teaching_assignments = ClassSubject.objects.filter(is_active=True)
            else:
                teaching_assignments = ClassSubject.objects.filter(
                    teacher=user, is_active=True
                )
            teaching_assignments = teaching_assignments.select_related('subject')
            subjects = Subject.objects.filter(
                pk__in=teaching_assignments.values_list('subject_id', flat=True)
            )

            selected_class_id = None
            if 'academic_class' in self.data:
                selected_class_id = self.data.get('academic_class')
            elif args and hasattr(args[0], 'get'):
                selected_class_id = args[0].get('academic_class')

            if selected_class_id:
                self.fields['test'].queryset = Test.objects.filter(
                    subject__in=subjects, is_active=True, academic_class_id=selected_class_id
                ).select_related('subject', 'term', 'academic_class')
            else:
                self.fields['test'].queryset = Test.objects.filter(
                    subject__in=subjects, is_active=True
                ).select_related('subject', 'term', 'academic_class')

            teacher_classes = AcademicClass.objects.filter(
                id__in=teaching_assignments.values_list('academic_class_id', flat=True).distinct(),
                is_active=True
            ).order_by('name')
            self.fields['academic_class'].choices = [
                (c.pk, c.name) for c in teacher_classes
            ]

            if selected_class_id:
                self.fields['student'].queryset = User.objects.filter(
                    profile__role=Profile.ROLE_STUDENT,
                    profile__academic_class_id=selected_class_id,
                    profile__status=Profile.STATUS_ACTIVE,
                ).select_related('profile').order_by('first_name', 'last_name', 'username')
                self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.profile.admission_number or 'No admission'})"
            else:
                self.fields['student'].queryset = User.objects.none()
                self.fields['student'].help_text = 'Select a class above to load students.'

        for field_name, field in self.fields.items():
            if field_name == 'academic_class':
                continue
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean_score(self):
        score = self.cleaned_data.get('score')
        test = self.cleaned_data.get('test')
        if score is not None and test:
            if score > test.max_score:
                raise forms.ValidationError(f'Score cannot exceed max score ({test.max_score}).')
        return score


class ExamResultForm(forms.ModelForm):
    academic_class = forms.ChoiceField(
        choices=[],
        required=False,
        label='Class',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_result_class'})
    )
    score = forms.IntegerField(
        min_value=0,
        label='Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '1'})
    )

    class Meta:
        model = ExamResult
        fields = ['student', 'exam', 'score']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user is not None:
            if user.is_superuser:
                teaching_assignments = ClassSubject.objects.filter(is_active=True)
            else:
                teaching_assignments = ClassSubject.objects.filter(
                    teacher=user, is_active=True
                )
            teaching_assignments = teaching_assignments.select_related('subject')
            subjects = Subject.objects.filter(
                pk__in=teaching_assignments.values_list('subject_id', flat=True)
            )

            selected_class_id = None
            if 'academic_class' in self.data:
                selected_class_id = self.data.get('academic_class')
            elif args and hasattr(args[0], 'get'):
                selected_class_id = args[0].get('academic_class')

            if selected_class_id:
                self.fields['exam'].queryset = Exam.objects.filter(
                    subject__in=subjects, is_active=True, academic_class_id=selected_class_id
                ).select_related('subject', 'term', 'academic_class')
            else:
                self.fields['exam'].queryset = Exam.objects.filter(
                    subject__in=subjects, is_active=True
                ).select_related('subject', 'term', 'academic_class')

            teacher_classes = AcademicClass.objects.filter(
                id__in=teaching_assignments.values_list('academic_class_id', flat=True).distinct(),
                is_active=True
            ).order_by('name')
            self.fields['academic_class'].choices = [
                (c.pk, c.name) for c in teacher_classes
            ]

            if selected_class_id:
                self.fields['student'].queryset = User.objects.filter(
                    profile__role=Profile.ROLE_STUDENT,
                    profile__academic_class_id=selected_class_id,
                    profile__status=Profile.STATUS_ACTIVE,
                ).select_related('profile').order_by('first_name', 'last_name', 'username')
                self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.profile.admission_number or 'No admission'})"
            else:
                self.fields['student'].queryset = User.objects.none()
                self.fields['student'].help_text = 'Select a class above to load students.'

        for field_name, field in self.fields.items():
            if field_name == 'academic_class':
                continue
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def clean_score(self):
        score = self.cleaned_data.get('score')
        exam = self.cleaned_data.get('exam')
        if score is not None and exam:
            if score > exam.max_score:
                raise forms.ValidationError(f'Score cannot exceed max score ({exam.max_score}).')
        return score


class PromotionDecisionForm(forms.ModelForm):
    class Meta:
        model = PromotionDecision
        fields = ['student', 'term', 'from_class', 'to_class', 'average_score',
                  'is_promoted', 'remarks', 'next_term_resumption_date']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class StaffCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    unique_id = forms.CharField(max_length=50, help_text='Admin-given Unique ID')
    phone = forms.CharField(max_length=20, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class AdminCreateStaffForm(forms.Form):
    unique_id = forms.CharField(max_length=50, help_text='Admin-given Unique ID for staff to use during registration')
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=20, required=False)
    gender = forms.ChoiceField(choices=Profile.GENDER_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class AdminCreateParentForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=20, required=False)
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(profile__role=Profile.ROLE_STUDENT, profile__status=Profile.STATUS_ACTIVE).select_related('profile', 'profile__academic_class'),
        required=False,
        label='Link to Student'
    )
    relationship = forms.ChoiceField(
        choices=[('father', 'Father'), ('mother', 'Mother'), ('guardian', 'Guardian')],
        required=False
    )
    is_primary = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} - {obj.profile.academic_class.name if obj.profile.academic_class else 'No class'}"
        self.fields['student'].widget.attrs.update({'size': '10'})
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class AdminCreateStudentForm(forms.Form):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    academic_class = forms.ModelChoiceField(
        queryset=AcademicClass.objects.filter(is_active=True),
        required=False
    )
    phone = forms.CharField(max_length=20, required=False)
    gender = forms.ChoiceField(choices=Profile.GENDER_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class GradeBoundaryForm(forms.ModelForm):
    class Meta:
        model = GradeBoundary
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class ResultRemarkForm(forms.ModelForm):
    class Meta:
        model = ResultRemark
        fields = ['student', 'term', 'academic_class', 'remark']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(
            profile__role=Profile.ROLE_STUDENT,
            profile__status=Profile.STATUS_ACTIVE
        ).select_related('profile')
        self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.profile.admission_number or 'No admission'})"
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})


class ParentProfileForm(forms.ModelForm):
    unique_id = forms.CharField(max_length=50, required=False, label='Invitation Code', help_text='Auto-generated if left blank')
    
    class Meta:
        model = ParentProfile
        fields = ['parent', 'student', 'relationship', 'phone', 'email', 'is_primary']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].queryset = User.objects.filter(
            profile__role=Profile.ROLE_PARENT
        ).select_related('profile').order_by('username')
        student_qs = User.objects.filter(
            profile__role=Profile.ROLE_STUDENT,
            profile__status=Profile.STATUS_ACTIVE
        ).select_related('profile')
        parent = None
        if self.instance and self.instance.pk:
            parent = self.instance.parent
        elif 'parent' in self.data:
            parent = self.data['parent']
        if parent:
            linked_students = ParentProfile.objects.filter(parent_id=parent).values_list('student_id', flat=True)
            if linked_students:
                student_qs = student_qs.filter(pk__in=linked_students)
        self.fields['student'].queryset = student_qs
        self.fields['parent'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.profile.get_role_display() if hasattr(obj, 'profile') else 'No role'})"
        self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.profile.admission_number or 'No admission'})"
        
        if self.instance and self.instance.pk:
            self.fields['unique_id'].initial = self.instance.parent.profile.unique_id
            self.fields['unique_id'].widget.attrs['readonly'] = True
        
        for field_name, field in self.fields.items():
            widget_name = field.widget.__class__.__name__
            if widget_name == 'Select':
                field.widget.attrs.update({'class': 'form-select'})
            elif widget_name == 'CheckboxInput':
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
        parent_profile = super().save(commit=False)
        unique_id = self.cleaned_data.get('unique_id')
        
        if commit:
            parent_profile.save()
            self.save_m2m()
            
            if unique_id:
                profile, created = Profile.objects.get_or_create(
                    user=parent_profile.parent,
                    defaults={'role': Profile.ROLE_PARENT}
                )
                profile.unique_id = unique_id
                profile.save()
        
        return parent_profile


class SchoolEventForm(forms.ModelForm):
    class Meta:
        model = SchoolEvent
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ('DateInput', 'Select'):
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-select'})


class FeeForm(forms.ModelForm):
    class Meta:
        model = Fee
        fields = '__all__'
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_class'].queryset = AcademicClass.objects.filter(is_active=True).order_by('name')
        self.fields['term'].queryset = Term.objects.all().order_by('-is_current', 'name')
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ('DateInput', 'Select'):
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-select'})

    def clean(self):
        cleaned_data = super().clean()
        fee_type = cleaned_data.get('fee_type')
        academic_class = cleaned_data.get('academic_class')
        term = cleaned_data.get('term')
        name = cleaned_data.get('name')

        if not name and fee_type and academic_class and term:
            type_label = dict(Fee.FEE_TYPE_CHOICES).get(fee_type, fee_type)
            cleaned_data['name'] = f"{academic_class.name} {type_label} - {term.get_name_display()}"

        return cleaned_data


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['student', 'fee', 'amount', 'status', 'transaction_id', 'payment_method', 'notes', 'paid_at']
        widgets = {
            'paid_at': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = User.objects.filter(
            profile__role=Profile.ROLE_STUDENT,
            profile__status=Profile.STATUS_ACTIVE
        ).select_related('profile')
        self.fields['student'].label_from_instance = lambda obj: f"{obj.get_full_name() or obj.username} ({obj.profile.admission_number or 'No admission'})"
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ('DateInput', 'Select'):
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-select'})
