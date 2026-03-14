from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.exams.models import Exam, ExamQuestion, ExamSession, ExamAnswer


class ExamQuestionInline(admin.TabularInline):
    model        = ExamQuestion
    extra        = 0
    fields       = ['question', 'order_index', 'score']
    ordering     = ['order_index']
    raw_id_fields = ['question']


class ExamAnswerInline(admin.TabularInline):
    model         = ExamAnswer
    extra         = 0
    fields        = ['question', 'is_correct', 'score_earned', 'graded_by', 'feedback']
    readonly_fields = ['question', 'answered_at']
    can_delete    = False


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display   = ['title_th', 'subject', 'status', 'time_limit_min',
                      'shuffle_questions', 'starts_at', 'ends_at', 'created_by']
    list_filter    = ['status', 'subject', 'shuffle_questions']
    search_fields  = ['title_th', 'title_en']
    readonly_fields = ['created_at', 'updated_at']
    inlines        = [ExamQuestionInline]
    fieldsets = (
        (_('ข้อมูลหลัก'), {
            'fields': ('title_th', 'title_en', 'description', 'subject', 'status')
        }),
        (_('การตั้งค่า'), {
            'fields': ('time_limit_min', 'total_score', 'pass_score',
                       'shuffle_questions', 'shuffle_choices',
                       'show_result', 'max_attempts')
        }),
        (_('ช่วงเวลา'), {
            'fields': ('starts_at', 'ends_at'),
            'classes': ('collapse',),
        }),
        (_('Metadata'), {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display  = ['exam', 'question', 'order_index', 'score']
    list_filter   = ['exam']
    ordering      = ['exam', 'order_index']
    raw_id_fields = ['question']


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display    = ['user', 'exam', 'attempt_number', 'status',
                       'total_score', 'is_passed', 'started_at', 'submitted_at']
    list_filter     = ['status', 'is_passed', 'exam']
    search_fields   = ['user__username', 'exam__title_th']
    readonly_fields = ['started_at', 'question_order']
    inlines         = [ExamAnswerInline]


@admin.register(ExamAnswer)
class ExamAnswerAdmin(admin.ModelAdmin):
    list_display    = ['session', 'question', 'is_correct', 'score_earned', 'graded_by']
    list_filter     = ['is_correct']
    search_fields   = ['session__user__username']
    readonly_fields = ['session', 'question', 'answered_at']
