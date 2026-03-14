import django_filters
from django.db.models import Q

from apps.questions.models import (
    Question,
    MultipleChoiceQuestion, EssayQuestion,
    TrueFalseQuestion, FillInBlankQuestion, MatchingQuestion,
)

QUESTION_TYPE_MAP = {
    'multiple_choice': MultipleChoiceQuestion,
    'essay':           EssayQuestion,
    'true_false':      TrueFalseQuestion,
    'fill_in_blank':   FillInBlankQuestion,
    'matching':        MatchingQuestion,
}


class QuestionFilter(django_filters.FilterSet):
    subject        = django_filters.NumberFilter(field_name='subject_id')
    topic          = django_filters.NumberFilter(field_name='topic_id')
    type           = django_filters.CharFilter(method='filter_by_type')
    tags           = django_filters.CharFilter(method='filter_by_tags')
    difficulty     = django_filters.ChoiceFilter(choices=Question.Difficulty.choices)
    created_after  = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    search         = django_filters.CharFilter(method='filter_search')

    class Meta:
        model  = Question
        fields = ['subject', 'topic', 'difficulty', 'is_active']

    def filter_by_type(self, queryset, name, value):
        """?type=multiple_choice | essay | true_false | fill_in_blank | matching"""
        model_class = QUESTION_TYPE_MAP.get(value)
        if model_class:
            return queryset.instance_of(model_class)
        return queryset

    def filter_by_tags(self, queryset, name, value):
        """?tags=พีชคณิต,วงกลม (คั่นด้วยจุลภาค)"""
        tags = [t.strip() for t in value.split(',') if t.strip()]
        q = Q()
        for tag in tags:
            q |= Q(tags__contains=tag)
        return queryset.filter(q)

    def filter_search(self, queryset, name, value):
        """?search=คำค้น — ค้นใน body_th, body_en, source"""
        return queryset.filter(
            Q(body_th__icontains=value) |
            Q(body_en__icontains=value) |
            Q(source__icontains=value)
        )
