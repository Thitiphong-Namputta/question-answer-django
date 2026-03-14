from django.db import transaction
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.questions.filters import QuestionFilter, QUESTION_TYPE_MAP
from apps.questions.models import (
    Question,
    MultipleChoiceQuestion, Choice,
    FillInBlankQuestion, MatchingQuestion,
)
from apps.questions.permissions import IsTeacherOrAdmin, IsOwnerOrTeacherOrAdmin
from apps.questions.serializers import (
    QuestionListSerializer, QuestionPolymorphicSerializer,
    SERIALIZER_MAP, QUESTION_TYPE_MAP as TYPE_LABEL_MAP,
)


class QuestionViewSet(viewsets.ModelViewSet):
    """
    API สำหรับจัดการข้อสอบทุกประเภท

    GET    /api/v1/questions/              — list + filter + search
    POST   /api/v1/questions/              — create (ระบุ question_type)
    GET    /api/v1/questions/{id}/         — retrieve
    PATCH  /api/v1/questions/{id}/         — update
    DELETE /api/v1/questions/{id}/         — soft delete

    Extra:
    POST   /api/v1/questions/random/       — สุ่มข้อสอบ
    DELETE /api/v1/questions/bulk-delete/  — ลบหลายข้อ
    GET    /api/v1/questions/stats/        — สถิติคลัง
    POST   /api/v1/questions/{id}/duplicate/ — ทำสำเนา
    """

    queryset        = Question.objects.select_related('subject', 'topic', 'created_by').all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = QuestionFilter
    ordering_fields = ['created_at', 'difficulty', 'score', 'subject']
    ordering        = ['-created_at']
    parser_classes  = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'stats'):
            return [IsAuthenticated()]
        if self.action == 'destroy':
            return [IsOwnerOrTeacherOrAdmin()]
        return [IsTeacherOrAdmin()]

    def get_serializer_class(self):
        if self.action == 'list':
            return QuestionListSerializer
        return QuestionPolymorphicSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'student':
            qs = qs.filter(is_active=True)
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = QuestionPolymorphicSerializer(instance, context={'request': request})
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        question_type    = request.data.get('question_type')
        serializer_class = SERIALIZER_MAP.get(question_type)

        if not serializer_class:
            return Response(
                {'question_type': f'ไม่รองรับประเภท "{question_type}" — ระบุได้: {", ".join(SERIALIZER_MAP.keys())}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial  = kwargs.pop('partial', False)
        instance = self.get_object()

        type_key         = TYPE_LABEL_MAP.get(instance.__class__.__name__)
        serializer_class = SERIALIZER_MAP.get(type_key)
        if not serializer_class:
            return Response({'detail': 'ไม่สามารถระบุประเภทข้อสอบได้'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = serializer_class(
            instance, data=request.data,
            partial=partial, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        """Soft delete — ตั้ง is_active=False แทนการลบจริง"""
        instance.is_active = False
        instance.save()

    # ──────────────────────────────────────────────────────────────────────────
    # Extra Actions
    # ──────────────────────────────────────────────────────────────────────────

    @action(detail=False, methods=['post'], url_path='random')
    def random(self, request):
        """
        POST /api/v1/questions/random/
        Body: { subject_id, topic_id?, difficulty?, question_type?, tags?, count }
        """
        data       = request.data
        subject_id = data.get('subject_id')
        count      = int(data.get('count', 10))

        if not subject_id:
            return Response({'subject_id': 'field นี้จำเป็น'}, status=status.HTTP_400_BAD_REQUEST)
        if not (1 <= count <= 100):
            return Response({'count': 'ต้องอยู่ระหว่าง 1–100'}, status=status.HTTP_400_BAD_REQUEST)

        qs = Question.objects.filter(subject_id=subject_id, is_active=True)

        if topic_id := data.get('topic_id'):
            qs = qs.filter(topic_id=topic_id)
        if difficulty := data.get('difficulty'):
            qs = qs.filter(difficulty=difficulty)
        if question_type := data.get('question_type'):
            model_class = QUESTION_TYPE_MAP.get(question_type)
            if model_class:
                qs = qs.instance_of(model_class)
        if tags := data.get('tags', []):
            q = Q()
            for tag in tags:
                q |= Q(tags__contains=tag)
            qs = qs.filter(q)

        total = qs.count()
        if total < count:
            return Response({
                'detail': f'ข้อสอบที่ตรงเงื่อนไขมีเพียง {total} ข้อ (ต้องการ {count} ข้อ)',
                'available': total,
            }, status=status.HTTP_400_BAD_REQUEST)

        questions  = qs.order_by('?')[:count]
        serializer = QuestionListSerializer(questions, many=True, context={'request': request})
        return Response({'count': count, 'questions': serializer.data})

    @action(detail=False, methods=['delete'], url_path='bulk-delete',
            permission_classes=[IsTeacherOrAdmin])
    def bulk_delete(self, request):
        """
        DELETE /api/v1/questions/bulk-delete/
        Body: { "ids": [1, 2, 3] }
        """
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'ids': 'field นี้จำเป็น'}, status=status.HTTP_400_BAD_REQUEST)

        qs = Question.objects.filter(id__in=ids)
        if request.user.role == 'teacher':
            qs = qs.filter(created_by=request.user)

        updated = qs.update(is_active=False)
        return Response({'deleted': updated})

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        GET /api/v1/questions/stats/
        ?subject_id=1 (optional)
        """
        qs = Question.objects.filter(is_active=True)
        if subject_id := request.query_params.get('subject_id'):
            qs = qs.filter(subject_id=subject_id)

        total      = qs.count()
        by_type    = qs.values('polymorphic_ctype__model').annotate(count=Count('id'))
        by_diff    = qs.values('difficulty').annotate(count=Count('id'))
        by_subject = qs.values('subject__name_th').annotate(count=Count('id'))

        return Response({
            'total':         total,
            'by_type':       list(by_type),
            'by_difficulty': list(by_diff),
            'by_subject':    list(by_subject),
        })

    @action(detail=True, methods=['post'], url_path='duplicate',
            permission_classes=[IsTeacherOrAdmin])
    @transaction.atomic
    def duplicate(self, request, pk=None):
        """POST /api/v1/questions/{id}/duplicate/ — ทำสำเนาข้อสอบ"""
        original_pk = pk
        original    = self.get_object()

        # ดึง nested objects ก่อน reset PK
        original_choices = list(original.choices.all()) if hasattr(original, 'choices') else []
        original_pairs   = list(original.pairs.all()) if hasattr(original, 'pairs') else []
        original_blanks  = list(original.blank_answers.all()) if hasattr(original, 'blank_answers') else []

        original.pk         = None
        original.created_by = request.user
        original.source     = f'(สำเนาจาก #{original_pk}) {original.source}'
        original.save()

        for choice in original_choices:
            choice.pk       = None
            choice.question = original
            choice.save()
        for pair in original_pairs:
            pair.pk       = None
            pair.question = original
            pair.save()
        for blank in original_blanks:
            blank.pk       = None
            blank.question = original
            blank.save()

        serializer = QuestionPolymorphicSerializer(original, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
