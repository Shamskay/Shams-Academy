from django.contrib import admin
from school.models import Term, AcademicClass, Subject, ClassSubject, ClassTeacher


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_current', 'start_date', 'end_date', 'next_term_start_date')
    list_filter = ('is_current', 'name')


@admin.register(AcademicClass)
class AcademicClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'section', 'next_class', 'is_active')
    list_filter = ('section', 'is_active')
    search_fields = ('name',)
    fields = ('name', 'section', 'next_class', 'is_active')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_core', 'is_active')
    search_fields = ('code', 'name')


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ('academic_class', 'subject', 'teacher', 'is_active')
    list_filter = ('academic_class', 'is_active')
    search_fields = ('academic_class__name', 'subject__name')


@admin.register(ClassTeacher)
class ClassTeacherAdmin(admin.ModelAdmin):
    list_display = ('academic_class', 'teacher', 'is_active')
    list_filter = ('academic_class', 'is_active')
