from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'admission_number', 'unique_id', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'admission_number', 'unique_id')
