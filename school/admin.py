from django.contrib import admin
from .models import (
    Test, Exam, TestResult, ExamResult,
    TermResult, PromotionDecision
)


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'term', 'academic_class', 'date', 'is_active')
    list_filter = ('term', 'academic_class', 'is_active')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'term', 'academic_class', 'date', 'is_active')
    list_filter = ('term', 'academic_class', 'is_active')


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'test', 'score', 'get_percentage', 'submitted_at')
    list_filter = ('test__term', 'test__academic_class')


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'get_percentage', 'submitted_at')
    list_filter = ('exam__term', 'exam__academic_class')


@admin.register(TermResult)
class TermResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'academic_class', 'average_score', 'total_subjects')
    list_filter = ('term', 'academic_class')


@admin.register(PromotionDecision)
class PromotionDecisionAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'from_class', 'to_class', 'average_score', 'is_promoted', 'next_term_resumption_date')
    list_filter = ('term', 'is_promoted', 'from_class', 'to_class')
