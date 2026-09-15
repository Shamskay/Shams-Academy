from django import forms
from django.contrib.auth.models import User
from django.db.models import Q

from accounts.models import Profile
from school.models import ClassSubject, AcademicClass, Subject, Term, StudyMaterial


class StudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = ['subject', 'academic_class', 'term', 'title', 'description', 'file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

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
            if field.widget.__class__.__name__ not in ('Textarea', 'ClearableFileInput', 'Select'):
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-select'})
