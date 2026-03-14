from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.questions.permissions import IsTeacherOrAdmin, IsAdminOnly
from apps.subjects.models import Subject, Topic
from apps.subjects.serializers import (
    SubjectSerializer, SubjectListSerializer,
    TopicSerializer, TopicFlatSerializer,
)


class SubjectViewSet(viewsets.ModelViewSet):
    """
    CRUD สำหรับ Subject

    GET    /api/v1/subjects/          — list
    POST   /api/v1/subjects/          — create (Teacher/Admin)
    GET    /api/v1/subjects/{id}/     — retrieve
    PATCH  /api/v1/subjects/{id}/     — update (Teacher/Admin)
    DELETE /api/v1/subjects/{id}/     — destroy (Admin)

    Extra:
    GET /api/v1/subjects/{id}/topics/      — tree
    GET /api/v1/subjects/{id}/topics/flat/ — flat list
    GET /api/v1/subjects/active/           — active only
    """

    queryset        = Subject.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ['name_th', 'name_en', 'code']
    ordering_fields = ['name_th', 'code', 'created_at']
    ordering        = ['name_th']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'topics', 'topics_flat', 'active'):
            return [IsAuthenticated()]
        if self.action == 'destroy':
            return [IsAdminOnly()]
        return [IsTeacherOrAdmin()]

    def get_serializer_class(self):
        if self.action == 'list':
            return SubjectListSerializer
        return SubjectSerializer

    def get_queryset(self):
        qs = Subject.objects.all()
        if self.request.user.role == 'student':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='topics')
    def topics(self, request, pk=None):
        """GET /api/v1/subjects/{id}/topics/ — nested tree"""
        subject = self.get_object()
        root_topics = subject.topics.filter(parent__isnull=True).order_by('order_index')
        return Response(TopicSerializer(root_topics, many=True).data)

    @action(detail=True, methods=['get'], url_path='topics/flat')
    def topics_flat(self, request, pk=None):
        """GET /api/v1/subjects/{id}/topics/flat/ — flat list (สำหรับ dropdown)"""
        subject = self.get_object()
        topics  = subject.topics.all().order_by('order_index', 'name_th')
        return Response(TopicFlatSerializer(topics, many=True).data)

    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """GET /api/v1/subjects/active/ — เฉพาะ active subjects"""
        subjects = Subject.objects.filter(is_active=True)
        return Response(SubjectListSerializer(subjects, many=True).data)


class TopicViewSet(viewsets.ModelViewSet):
    """
    CRUD สำหรับ Topic

    GET    /api/v1/topics/        — list (?subject=id)
    POST   /api/v1/topics/        — create (Teacher/Admin)
    GET    /api/v1/topics/{id}/   — retrieve
    PATCH  /api/v1/topics/{id}/   — update (Teacher/Admin)
    DELETE /api/v1/topics/{id}/   — destroy (Admin)
    """

    queryset         = Topic.objects.select_related('subject', 'parent').all()
    serializer_class = TopicFlatSerializer
    filter_backends  = [filters.SearchFilter, filters.OrderingFilter]
    search_fields    = ['name_th', 'name_en']
    ordering         = ['order_index', 'name_th']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action == 'destroy':
            return [IsAdminOnly()]
        return [IsTeacherOrAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        subject_id = self.request.query_params.get('subject')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs
