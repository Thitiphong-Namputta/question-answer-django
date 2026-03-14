from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.subjects.models import Subject, Topic


class TopicInline(admin.TabularInline):
    model    = Topic
    extra    = 2
    fields   = ['name_th', 'name_en', 'parent', 'order_index']
    ordering = ['order_index']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # กรอง parent ให้แสดงเฉพาะ topic ในวิชาเดียวกัน
        if db_field.name == 'parent' and request.resolver_match.kwargs.get('object_id'):
            subject_id = request.resolver_match.kwargs['object_id']
            kwargs['queryset'] = Topic.objects.filter(subject_id=subject_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display   = ['name_th', 'code', 'color', 'is_active', 'created_by', 'created_at']
    list_filter    = ['is_active']
    search_fields  = ['name_th', 'name_en', 'code']
    readonly_fields = ['created_at', 'updated_at']
    inlines        = [TopicInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display  = ['name_th', 'subject', 'parent', 'order_index']
    list_filter   = ['subject']
    search_fields = ['name_th', 'name_en']
    ordering      = ['subject', 'order_index']
