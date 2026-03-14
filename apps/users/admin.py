from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('ข้อมูลเพิ่มเติม'), {
            'fields': ('role', 'locale', 'avatar_url', 'bio')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('ข้อมูลเพิ่มเติม'), {
            'fields': ('role', 'locale')
        }),
    )
    list_display  = ['username', 'email', 'get_full_name', 'role', 'locale', 'is_active']
    list_filter   = ['role', 'locale', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
