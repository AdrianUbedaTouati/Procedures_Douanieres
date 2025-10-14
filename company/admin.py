from django.contrib import admin
from .models import CompanyProfile


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'size', 'is_complete', 'created_at']
    list_filter = ['size', 'is_complete', 'public_sector_experience']
    search_fields = ['company_name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
