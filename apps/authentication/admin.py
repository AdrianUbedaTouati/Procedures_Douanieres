from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetToken


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'email_verified', 'is_staff', 'created_at')
    list_filter = ('email_verified', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('email_verified', 'bio', 'avatar', 'phone')}),
        ('Login Security', {'fields': ('login_attempts', 'last_login_attempt', 'login_blocked_until')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('email',)}),
    )
    search_fields = ('username', 'email', 'phone')
    ordering = ('-created_at',)


class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'used')
    list_filter = ('used', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)


admin.site.register(User, UserAdmin)
admin.site.register(PasswordResetToken, PasswordResetTokenAdmin)
