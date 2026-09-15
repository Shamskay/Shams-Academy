from django.contrib import admin
from school.models import StudyMaterial


@admin.register(StudyMaterial)
class StudyMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'term', 'uploaded_by', 'is_active', 'created_at')
    list_filter = ('term', 'subject', 'is_active')
    search_fields = ('title',)
