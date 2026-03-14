from rest_framework import serializers

from apps.subjects.models import Subject, Topic


class TopicSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    depth    = serializers.SerializerMethodField()

    class Meta:
        model  = Topic
        fields = [
            'id', 'subject', 'parent',
            'name_th', 'name_en',
            'order_index', 'depth', 'children',
        ]
        read_only_fields = ['id']

    def get_children(self, obj):
        children = obj.children.all().order_by('order_index')
        if children.exists():
            return TopicSerializer(children, many=True).data
        return []

    def get_depth(self, obj):
        return obj.get_depth()


class TopicFlatSerializer(serializers.ModelSerializer):
    """Flat version สำหรับ dropdown/select"""

    class Meta:
        model  = Topic
        fields = ['id', 'name_th', 'name_en', 'parent', 'order_index']
        read_only_fields = ['id']


class SubjectSerializer(serializers.ModelSerializer):
    topics          = TopicFlatSerializer(many=True, read_only=True)
    topic_count     = serializers.SerializerMethodField()
    question_count  = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model  = Subject
        fields = [
            'id', 'name_th', 'name_en', 'code',
            'description', 'color', 'is_active',
            'topic_count', 'question_count',
            'topics',
            'created_by', 'created_by_name',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_topic_count(self, obj):
        return obj.topics.count()

    def get_question_count(self, obj):
        return obj.questions.filter(is_active=True).count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def validate_code(self, value):
        if value and not value.replace('-', '').replace('_', '').isalnum():
            raise serializers.ValidationError(
                'รหัสวิชาต้องประกอบด้วยตัวอักษรและตัวเลขเท่านั้น'
            )
        return value.upper() if value else value


class SubjectListSerializer(serializers.ModelSerializer):
    """Lightweight สำหรับ list endpoint"""

    topic_count    = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()

    class Meta:
        model  = Subject
        fields = [
            'id', 'name_th', 'name_en', 'code',
            'color', 'is_active',
            'topic_count', 'question_count',
        ]

    def get_topic_count(self, obj):
        return obj.topics.count()

    def get_question_count(self, obj):
        return obj.questions.filter(is_active=True).count()
