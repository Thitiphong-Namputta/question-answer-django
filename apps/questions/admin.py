from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin
from polymorphic.admin import (
    PolymorphicParentModelAdmin,
    PolymorphicChildModelAdmin,
    PolymorphicChildModelFilter,
)

from apps.questions.models import (
    Question,
    MultipleChoiceQuestion, Choice,
    EssayQuestion,
    TrueFalseQuestion,
    FillInBlankQuestion, BlankAnswer,
    MatchingQuestion, MatchingPair,
)


# =============================================================================
# Inlines
# =============================================================================

class ChoiceInline(admin.TabularInline):
    model   = Choice
    extra   = 4
    fields  = ['label', 'body_th', 'body_latex', 'image', 'is_correct', 'order_index']
    ordering = ['order_index']


class BlankAnswerInline(admin.TabularInline):
    model   = BlankAnswer
    extra   = 2
    fields  = ['blank_number', 'answer_text', 'order_index']
    ordering = ['blank_number', 'order_index']


class MatchingPairInline(admin.TabularInline):
    model   = MatchingPair
    extra   = 4
    fields  = ['left_body', 'left_image', 'right_body', 'right_image', 'order_index']
    ordering = ['order_index']


# =============================================================================
# Child Admins (แต่ละประเภทข้อสอบ)
# =============================================================================

@admin.register(MultipleChoiceQuestion)
class MultipleChoiceQuestionAdmin(PolymorphicChildModelAdmin):
    base_model = MultipleChoiceQuestion
    inlines    = [ChoiceInline]
    fieldsets  = (
        (_('ข้อมูลหลัก'), {
            'fields': ('subject', 'topic', 'difficulty', 'answer_mode', 'score')
        }),
        (_('โจทย์'), {
            'fields': ('body_th', 'body_en', 'body_latex', 'image')
        }),
        (_('เฉลย'), {
            'fields': ('explanation_th', 'explanation_en', 'explanation_latex', 'explanation_image'),
            'classes': ('collapse',),
        }),
        (_('Metadata'), {
            'fields': ('tags', 'source', 'is_active'),
            'classes': ('collapse',),
        }),
    )


@admin.register(EssayQuestion)
class EssayQuestionAdmin(PolymorphicChildModelAdmin):
    base_model = EssayQuestion
    fieldsets  = (
        (_('ข้อมูลหลัก'), {'fields': ('subject', 'topic', 'difficulty', 'score')}),
        (_('โจทย์'), {'fields': ('body_th', 'body_en', 'body_latex', 'image')}),
        (_('เกณฑ์การให้คะแนน'), {
            'fields': ('sample_answer', 'grading_rubric', 'max_words')
        }),
        (_('Metadata'), {
            'fields': ('tags', 'source', 'is_active'),
            'classes': ('collapse',),
        }),
    )


@admin.register(TrueFalseQuestion)
class TrueFalseQuestionAdmin(PolymorphicChildModelAdmin):
    base_model = TrueFalseQuestion
    fieldsets  = (
        (_('ข้อมูลหลัก'), {'fields': ('subject', 'topic', 'difficulty', 'score')}),
        (_('โจทย์'), {'fields': ('body_th', 'body_en', 'body_latex', 'image')}),
        (_('คำตอบ'), {'fields': ('correct_answer', 'true_label', 'false_label')}),
        (_('เฉลย'), {
            'fields': ('explanation_th', 'explanation_en'),
            'classes': ('collapse',),
        }),
        (_('Metadata'), {
            'fields': ('tags', 'source', 'is_active'),
            'classes': ('collapse',),
        }),
    )


@admin.register(FillInBlankQuestion)
class FillInBlankQuestionAdmin(PolymorphicChildModelAdmin):
    base_model = FillInBlankQuestion
    inlines    = [BlankAnswerInline]
    fieldsets  = (
        (_('ข้อมูลหลัก'), {'fields': ('subject', 'topic', 'difficulty', 'score')}),
        (_('โจทย์'), {
            'fields': ('body_th', 'body_en', 'body_latex', 'image'),
            'description': _('ใช้ {{1}}, {{2}}, ... แทนช่องว่าง'),
        }),
        (_('การตรวจคำตอบ'), {'fields': ('grading_mode',)}),
        (_('เฉลย'), {
            'fields': ('explanation_th', 'explanation_en'),
            'classes': ('collapse',),
        }),
        (_('Metadata'), {
            'fields': ('tags', 'source', 'is_active'),
            'classes': ('collapse',),
        }),
    )


@admin.register(MatchingQuestion)
class MatchingQuestionAdmin(PolymorphicChildModelAdmin):
    base_model = MatchingQuestion
    inlines    = [MatchingPairInline]
    fieldsets  = (
        (_('ข้อมูลหลัก'), {'fields': ('subject', 'topic', 'difficulty', 'score')}),
        (_('โจทย์'), {'fields': ('body_th', 'body_en', 'body_latex', 'image')}),
        (_('การตั้งค่า'), {'fields': ('shuffle_right',)}),
        (_('เฉลย'), {
            'fields': ('explanation_th', 'explanation_en'),
            'classes': ('collapse',),
        }),
        (_('Metadata'), {
            'fields': ('tags', 'source', 'is_active'),
            'classes': ('collapse',),
        }),
    )


# =============================================================================
# Parent Admin (รวมทุกประเภท)
# =============================================================================

@admin.register(Question)
class QuestionParentAdmin(PolymorphicParentModelAdmin, ImportExportModelAdmin):
    base_model   = Question
    child_models = (
        MultipleChoiceQuestion,
        EssayQuestion,
        TrueFalseQuestion,
        FillInBlankQuestion,
        MatchingQuestion,
    )
    list_display   = ['__str__', 'subject', 'topic', 'difficulty', 'score', 'is_active', 'created_at']
    list_filter    = [PolymorphicChildModelFilter, 'difficulty', 'subject', 'is_active']
    search_fields  = ['body_th', 'body_en', 'source']
    list_per_page  = 30
    date_hierarchy = 'created_at'
