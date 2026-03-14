from rest_framework import serializers

from apps.subjects.serializers import SubjectListSerializer, TopicFlatSerializer
from apps.questions.models import (
    Question,
    MultipleChoiceQuestion, Choice,
    EssayQuestion,
    TrueFalseQuestion,
    FillInBlankQuestion, BlankAnswer,
    MatchingQuestion, MatchingPair,
)

# Map จาก class name → question_type string
QUESTION_TYPE_MAP = {
    'MultipleChoiceQuestion': 'multiple_choice',
    'EssayQuestion':          'essay',
    'TrueFalseQuestion':      'true_false',
    'FillInBlankQuestion':    'fill_in_blank',
    'MatchingQuestion':       'matching',
}


# =============================================================================
# Child Serializers
# =============================================================================

class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Choice
        fields = ['id', 'label', 'body_th', 'body_en', 'body_latex', 'image',
                  'is_correct', 'order_index']
        read_only_fields = ['id']


class ChoiceReadSerializer(serializers.ModelSerializer):
    """สำหรับผู้สอบ — ไม่แสดง is_correct"""
    class Meta:
        model  = Choice
        fields = ['id', 'label', 'body_th', 'body_en', 'body_latex', 'image', 'order_index']


class BlankAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BlankAnswer
        fields = ['id', 'blank_number', 'answer_text', 'order_index']
        read_only_fields = ['id']


class MatchingPairSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MatchingPair
        fields = ['id', 'left_body', 'left_image', 'right_body', 'right_image', 'order_index']
        read_only_fields = ['id']


class MatchingPairReadSerializer(serializers.ModelSerializer):
    """สำหรับผู้สอบ — ไม่เปิดเผยลำดับที่ถูกต้อง"""
    class Meta:
        model  = MatchingPair
        fields = ['id', 'left_body', 'left_image', 'right_body', 'right_image']


# =============================================================================
# Base Question Serializer
# =============================================================================

class QuestionBaseSerializer(serializers.ModelSerializer):
    subject_detail     = SubjectListSerializer(source='subject', read_only=True)
    topic_detail       = TopicFlatSerializer(source='topic', read_only=True)
    question_type      = serializers.SerializerMethodField()
    created_by_name    = serializers.SerializerMethodField()
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)

    class Meta:
        model  = Question
        fields = [
            'id', 'question_type',
            'subject', 'subject_detail',
            'topic', 'topic_detail',
            'difficulty', 'difficulty_display',
            'body_th', 'body_en', 'body_latex', 'image',
            'explanation_th', 'explanation_en', 'explanation_latex', 'explanation_image',
            'score', 'tags', 'source', 'is_active',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_question_type(self, obj):
        return QUESTION_TYPE_MAP.get(obj.__class__.__name__, 'unknown')

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


# =============================================================================
# Multiple Choice
# =============================================================================

class MultipleChoiceQuestionSerializer(QuestionBaseSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta(QuestionBaseSerializer.Meta):
        model  = MultipleChoiceQuestion
        fields = QuestionBaseSerializer.Meta.fields + ['answer_mode', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = MultipleChoiceQuestion.objects.create(**validated_data)
        for c in choices_data:
            Choice.objects.create(question=question, **c)
        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if choices_data is not None:
            instance.choices.all().delete()
            for c in choices_data:
                Choice.objects.create(question=instance, **c)
        return instance

    def validate_choices(self, value):
        if len(value) < 2:
            raise serializers.ValidationError('ต้องมีตัวเลือกอย่างน้อย 2 ตัวเลือก')
        if not any(c.get('is_correct') for c in value):
            raise serializers.ValidationError('ต้องมีตัวเลือกที่ถูกต้องอย่างน้อย 1 ตัวเลือก')
        return value


class MultipleChoiceQuestionReadSerializer(MultipleChoiceQuestionSerializer):
    """สำหรับผู้สอบ — ซ่อนเฉลยและ is_correct"""
    choices = ChoiceReadSerializer(many=True)

    class Meta(MultipleChoiceQuestionSerializer.Meta):
        fields = [f for f in MultipleChoiceQuestionSerializer.Meta.fields
                  if f not in ('explanation_th', 'explanation_en',
                               'explanation_latex', 'explanation_image')]


# =============================================================================
# Essay
# =============================================================================

class EssayQuestionSerializer(QuestionBaseSerializer):
    class Meta(QuestionBaseSerializer.Meta):
        model  = EssayQuestion
        fields = QuestionBaseSerializer.Meta.fields + [
            'sample_answer', 'max_words', 'grading_rubric'
        ]

    def create(self, validated_data):
        return EssayQuestion.objects.create(**validated_data)


class EssayQuestionReadSerializer(EssayQuestionSerializer):
    """สำหรับผู้สอบ — ซ่อน sample_answer และ rubric"""
    class Meta(EssayQuestionSerializer.Meta):
        fields = [f for f in EssayQuestionSerializer.Meta.fields
                  if f not in ('sample_answer', 'grading_rubric',
                               'explanation_th', 'explanation_en',
                               'explanation_latex', 'explanation_image')]


# =============================================================================
# True/False
# =============================================================================

class TrueFalseQuestionSerializer(QuestionBaseSerializer):
    class Meta(QuestionBaseSerializer.Meta):
        model  = TrueFalseQuestion
        fields = QuestionBaseSerializer.Meta.fields + [
            'correct_answer', 'true_label', 'false_label'
        ]

    def create(self, validated_data):
        return TrueFalseQuestion.objects.create(**validated_data)


class TrueFalseQuestionReadSerializer(TrueFalseQuestionSerializer):
    """สำหรับผู้สอบ — ซ่อนคำตอบ"""
    class Meta(TrueFalseQuestionSerializer.Meta):
        fields = [f for f in TrueFalseQuestionSerializer.Meta.fields
                  if f not in ('correct_answer',
                               'explanation_th', 'explanation_en',
                               'explanation_latex', 'explanation_image')]


# =============================================================================
# Fill in the Blank
# =============================================================================

class FillInBlankQuestionSerializer(QuestionBaseSerializer):
    blank_answers = BlankAnswerSerializer(many=True)
    blank_count   = serializers.SerializerMethodField()

    class Meta(QuestionBaseSerializer.Meta):
        model  = FillInBlankQuestion
        fields = QuestionBaseSerializer.Meta.fields + [
            'grading_mode', 'blank_count', 'blank_answers'
        ]

    def get_blank_count(self, obj):
        return obj.get_blank_count()

    def create(self, validated_data):
        blank_answers_data = validated_data.pop('blank_answers', [])
        question = FillInBlankQuestion.objects.create(**validated_data)
        for ba in blank_answers_data:
            BlankAnswer.objects.create(question=question, **ba)
        return question

    def update(self, instance, validated_data):
        blank_answers_data = validated_data.pop('blank_answers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if blank_answers_data is not None:
            instance.blank_answers.all().delete()
            for ba in blank_answers_data:
                BlankAnswer.objects.create(question=instance, **ba)
        return instance


class FillInBlankQuestionReadSerializer(FillInBlankQuestionSerializer):
    """สำหรับผู้สอบ — ซ่อนคำตอบ"""
    class Meta(FillInBlankQuestionSerializer.Meta):
        fields = [f for f in FillInBlankQuestionSerializer.Meta.fields
                  if f not in ('blank_answers',
                               'explanation_th', 'explanation_en',
                               'explanation_latex', 'explanation_image')]


# =============================================================================
# Matching
# =============================================================================

class MatchingQuestionSerializer(QuestionBaseSerializer):
    pairs = MatchingPairSerializer(many=True)

    class Meta(QuestionBaseSerializer.Meta):
        model  = MatchingQuestion
        fields = QuestionBaseSerializer.Meta.fields + ['shuffle_right', 'pairs']

    def create(self, validated_data):
        pairs_data = validated_data.pop('pairs', [])
        question = MatchingQuestion.objects.create(**validated_data)
        for p in pairs_data:
            MatchingPair.objects.create(question=question, **p)
        return question

    def update(self, instance, validated_data):
        pairs_data = validated_data.pop('pairs', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if pairs_data is not None:
            instance.pairs.all().delete()
            for p in pairs_data:
                MatchingPair.objects.create(question=instance, **p)
        return instance

    def validate_pairs(self, value):
        if len(value) < 2:
            raise serializers.ValidationError('ต้องมีคู่จับคู่อย่างน้อย 2 คู่')
        return value


class MatchingQuestionReadSerializer(MatchingQuestionSerializer):
    """สำหรับผู้สอบ — สุ่มลำดับขวา (ถ้า shuffle_right=True)"""
    pairs = serializers.SerializerMethodField()

    def get_pairs(self, obj):
        import random
        left_items  = [{'id': p.id, 'left_body': p.left_body,
                        'left_image': p.left_image.url if p.left_image else None}
                       for p in obj.pairs.all()]
        right_items = [{'id': p.id, 'right_body': p.right_body,
                        'right_image': p.right_image.url if p.right_image else None}
                       for p in obj.pairs.all()]
        if obj.shuffle_right:
            random.shuffle(right_items)
        return {'left': left_items, 'right': right_items}

    class Meta(MatchingQuestionSerializer.Meta):
        fields = [f for f in MatchingQuestionSerializer.Meta.fields
                  if f not in ('explanation_th', 'explanation_en',
                               'explanation_latex', 'explanation_image')]


# =============================================================================
# Polymorphic Dispatcher
# =============================================================================

SERIALIZER_MAP = {
    'multiple_choice': MultipleChoiceQuestionSerializer,
    'essay':           EssayQuestionSerializer,
    'true_false':      TrueFalseQuestionSerializer,
    'fill_in_blank':   FillInBlankQuestionSerializer,
    'matching':        MatchingQuestionSerializer,
}

READ_SERIALIZER_MAP = {
    'multiple_choice': MultipleChoiceQuestionReadSerializer,
    'essay':           EssayQuestionReadSerializer,
    'true_false':      TrueFalseQuestionReadSerializer,
    'fill_in_blank':   FillInBlankQuestionReadSerializer,
    'matching':        MatchingQuestionReadSerializer,
}


class QuestionPolymorphicSerializer(serializers.Serializer):
    """
    Dispatcher — เลือก serializer ที่เหมาะสมตาม question_type
    ใช้สำหรับ GET (retrieve) และ list
    """

    @classmethod
    def get_serializer_class(cls, obj, read_only=False):
        key = QUESTION_TYPE_MAP.get(obj.__class__.__name__)
        if read_only:
            return READ_SERIALIZER_MAP.get(key)
        return SERIALIZER_MAP.get(key)

    def to_representation(self, obj):
        request     = self.context.get('request')
        is_student  = request and hasattr(request.user, 'role') and request.user.role == 'student'
        serializer_class = self.get_serializer_class(obj, read_only=is_student)
        if serializer_class:
            return serializer_class(obj, context=self.context).data
        return {}


# =============================================================================
# Question List Serializer (Lightweight)
# =============================================================================

class QuestionListSerializer(serializers.ModelSerializer):
    """ใช้สำหรับ list endpoint — ไม่รวม nested fields เพื่อ performance"""

    question_type      = serializers.SerializerMethodField()
    subject_name       = serializers.CharField(source='subject.name_th', read_only=True)
    topic_name         = serializers.CharField(source='topic.name_th', read_only=True, default=None)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    preview            = serializers.SerializerMethodField()

    class Meta:
        model  = Question
        fields = [
            'id', 'question_type',
            'subject', 'subject_name',
            'topic', 'topic_name',
            'difficulty', 'difficulty_display',
            'preview', 'score', 'tags', 'source', 'is_active',
            'created_at',
        ]

    def get_question_type(self, obj):
        return QUESTION_TYPE_MAP.get(obj.__class__.__name__, 'unknown')

    def get_preview(self, obj):
        text = obj.body_th or ''
        return text[:80] + '...' if len(text) > 80 else text
