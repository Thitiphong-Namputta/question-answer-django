from django.utils import timezone
from rest_framework import serializers

from apps.exams.models import Exam, ExamQuestion, ExamSession, ExamAnswer
from apps.questions.serializers import QuestionPolymorphicSerializer, QuestionListSerializer
from apps.questions.models import Question, Choice


# =============================================================================
# Exam Serializers
# =============================================================================

class ExamQuestionSerializer(serializers.ModelSerializer):
    question_preview = serializers.SerializerMethodField()
    effective_score  = serializers.SerializerMethodField()

    class Meta:
        model  = ExamQuestion
        fields = ['id', 'question', 'question_preview', 'order_index', 'score', 'effective_score']
        read_only_fields = ['id']

    def get_question_preview(self, obj):
        text = obj.question.body_th or ''
        return text[:80] + '...' if len(text) > 80 else text

    def get_effective_score(self, obj):
        return obj.get_score()


class ExamSerializer(serializers.ModelSerializer):
    exam_questions   = ExamQuestionSerializer(many=True, read_only=True)
    question_count   = serializers.SerializerMethodField()
    total_score_calc = serializers.SerializerMethodField()
    created_by_name  = serializers.SerializerMethodField()
    is_available     = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Exam
        fields = [
            'id', 'title_th', 'title_en', 'description', 'subject',
            'time_limit_min', 'total_score', 'pass_score',
            'shuffle_questions', 'shuffle_choices',
            'show_result', 'max_attempts',
            'starts_at', 'ends_at', 'status', 'is_available',
            'question_count', 'total_score_calc',
            'exam_questions',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_question_count(self, obj):
        return obj.exam_questions.count()

    def get_total_score_calc(self, obj):
        return obj.get_total_score()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class ExamListSerializer(serializers.ModelSerializer):
    """Lightweight สำหรับ list"""
    question_count  = serializers.SerializerMethodField()
    is_available    = serializers.BooleanField(read_only=True)
    subject_name    = serializers.CharField(source='subject.name_th', read_only=True, default=None)

    class Meta:
        model  = Exam
        fields = [
            'id', 'title_th', 'title_en', 'subject', 'subject_name',
            'status', 'is_available', 'time_limit_min',
            'starts_at', 'ends_at', 'question_count',
        ]

    def get_question_count(self, obj):
        return obj.exam_questions.count()


class AddQuestionSerializer(serializers.Serializer):
    """สำหรับ POST /exams/{id}/questions/"""
    question_id = serializers.IntegerField()
    score       = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    order_index = serializers.IntegerField(required=False, default=0)

    def validate_question_id(self, value):
        if not Question.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('ไม่พบข้อสอบที่ระบุ')
        return value


class RandomQuestionSerializer(serializers.Serializer):
    """สำหรับ POST /exams/{id}/questions/random/"""
    subject_id    = serializers.IntegerField(required=False, allow_null=True)
    topic_id      = serializers.IntegerField(required=False, allow_null=True)
    difficulty    = serializers.ChoiceField(choices=['easy', 'medium', 'hard'], required=False, allow_null=True)
    question_type = serializers.ChoiceField(
        choices=['multiple_choice', 'essay', 'true_false', 'fill_in_blank', 'matching'],
        required=False, allow_null=True,
    )
    count = serializers.IntegerField(min_value=1, max_value=100)


# =============================================================================
# ExamSession Serializers
# =============================================================================

class ExamAnswerSerializer(serializers.ModelSerializer):
    """คำตอบในการแสดงผล"""
    question_preview = serializers.SerializerMethodField()

    class Meta:
        model  = ExamAnswer
        fields = [
            'id', 'question', 'question_preview',
            'answer_choice', 'answer_text', 'answer_boolean', 'answer_matching',
            'is_correct', 'score_earned',
            'graded_by', 'graded_at', 'feedback',
            'answered_at',
        ]
        read_only_fields = ['id', 'is_correct', 'score_earned', 'graded_by', 'graded_at', 'answered_at']

    def get_question_preview(self, obj):
        text = obj.question.body_th or ''
        return text[:60] + '...' if len(text) > 60 else text


class SubmitAnswerSerializer(serializers.Serializer):
    """สำหรับ PATCH /sessions/{id}/answers/{qid}/ — บันทึกคำตอบทีละข้อ"""
    answer_choice    = serializers.IntegerField(required=False, allow_null=True)
    answer_choices   = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )
    answer_text      = serializers.CharField(required=False, allow_blank=True)
    answer_boolean   = serializers.BooleanField(required=False, allow_null=True)
    answer_matching  = serializers.ListField(required=False, allow_null=True)

    def validate_answer_choice(self, value):
        if value and not Choice.objects.filter(id=value).exists():
            raise serializers.ValidationError('ไม่พบตัวเลือกที่ระบุ')
        return value


class ExamSessionSerializer(serializers.ModelSerializer):
    """Session detail พร้อมข้อสอบ (สำหรับผู้สอบ)"""
    questions    = serializers.SerializerMethodField()
    time_left    = serializers.SerializerMethodField()
    exam_title   = serializers.CharField(source='exam.title_th', read_only=True)

    class Meta:
        model  = ExamSession
        fields = [
            'id', 'exam', 'exam_title',
            'attempt_number', 'status',
            'started_at', 'submitted_at', 'expires_at',
            'total_score', 'is_passed',
            'time_left', 'questions',
        ]
        read_only_fields = ['id', 'started_at', 'attempt_number', 'total_score', 'is_passed']

    def get_time_left(self, obj):
        """เวลาที่เหลือ (วินาที) หรือ None ถ้าไม่จำกัดเวลา"""
        if not obj.expires_at:
            return None
        from django.utils import timezone
        remaining = (obj.expires_at - timezone.now()).total_seconds()
        return max(0, int(remaining))

    def get_questions(self, obj):
        """ดึงข้อสอบตามลำดับที่ snapshot ไว้"""
        request = self.context.get('request')
        q_ids   = obj.question_order

        if not q_ids:
            exam_qs = obj.exam.exam_questions.select_related('question').order_by('order_index')
            q_ids   = [eq.question_id for eq in exam_qs]

        questions = {q.id: q for q in Question.objects.filter(id__in=q_ids)}
        ordered   = [questions[qid] for qid in q_ids if qid in questions]

        return QuestionPolymorphicSerializer(ordered, many=True, context={'request': request}).data


class ExamSessionListSerializer(serializers.ModelSerializer):
    """Lightweight session สำหรับ list"""
    user_name  = serializers.CharField(source='user.get_full_name', read_only=True)
    exam_title = serializers.CharField(source='exam.title_th', read_only=True)

    class Meta:
        model  = ExamSession
        fields = [
            'id', 'exam', 'exam_title', 'user', 'user_name',
            'attempt_number', 'status',
            'total_score', 'is_passed',
            'started_at', 'submitted_at',
        ]


class SessionResultSerializer(serializers.ModelSerializer):
    """ผลการสอบพร้อมคำตอบทั้งหมด"""
    answers    = ExamAnswerSerializer(many=True, read_only=True)
    exam_title = serializers.CharField(source='exam.title_th', read_only=True)
    pass_score = serializers.DecimalField(source='exam.pass_score', max_digits=7, decimal_places=2, read_only=True)

    class Meta:
        model  = ExamSession
        fields = [
            'id', 'exam', 'exam_title',
            'attempt_number', 'status',
            'total_score', 'pass_score', 'is_passed',
            'started_at', 'submitted_at',
            'answers',
        ]


class GradeAnswerSerializer(serializers.Serializer):
    """สำหรับครูตรวจข้อสอบอัตนัย"""
    score_earned = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0)
    feedback     = serializers.CharField(required=False, allow_blank=True)
