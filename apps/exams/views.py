import random

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.exams.models import Exam, ExamQuestion, ExamSession, ExamAnswer
from apps.exams.serializers import (
    ExamSerializer, ExamListSerializer,
    AddQuestionSerializer, RandomQuestionSerializer,
    ExamSessionSerializer, ExamSessionListSerializer,
    SessionResultSerializer, SubmitAnswerSerializer,
    GradeAnswerSerializer,
)
from apps.questions.filters import QUESTION_TYPE_MAP
from apps.questions.models import Question
from apps.questions.permissions import IsTeacherOrAdmin, IsAdminOnly


# =============================================================================
# ExamViewSet
# =============================================================================

class ExamViewSet(viewsets.ModelViewSet):
    """
    CRUD สำหรับชุดข้อสอบ

    GET    /api/v1/exams/                     — list
    POST   /api/v1/exams/                     — create (Teacher/Admin)
    GET    /api/v1/exams/{id}/                — retrieve
    PATCH  /api/v1/exams/{id}/                — update (Teacher/Admin)
    DELETE /api/v1/exams/{id}/                — destroy (Admin)

    POST   /api/v1/exams/{id}/publish/        — เผยแพร่
    POST   /api/v1/exams/{id}/questions/      — เพิ่มข้อสอบ
    DELETE /api/v1/exams/{id}/questions/{qid}/ — ลบข้อสอบออกจากชุด
    POST   /api/v1/exams/{id}/questions/random/ — สุ่มข้อสอบเข้าชุด
    POST   /api/v1/exams/{id}/sessions/       — เริ่มสอบ (Student)
    GET    /api/v1/exams/{id}/sessions/       — ดูผลทุก session (Teacher/Admin)
    """

    queryset        = Exam.objects.select_related('subject', 'created_by').all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields   = ['title_th', 'title_en']
    ordering_fields = ['created_at', 'starts_at', 'status']
    ordering        = ['-created_at']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        if self.action == 'destroy':
            return [IsAdminOnly()]
        if self.action in ('start_session',):
            return [IsAuthenticated()]
        return [IsTeacherOrAdmin()]

    def get_serializer_class(self):
        if self.action == 'list':
            return ExamListSerializer
        return ExamSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'student':
            qs = qs.filter(status=Exam.Status.PUBLISHED)
        subject_id = self.request.query_params.get('subject')
        if subject_id:
            qs = qs.filter(subject_id=subject_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # ── Exam management actions ───────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='publish')
    def publish(self, request, pk=None):
        """POST /api/v1/exams/{id}/publish/ — เผยแพร่ชุดข้อสอบ"""
        exam = self.get_object()
        if exam.exam_questions.count() == 0:
            return Response({'detail': 'ต้องมีข้อสอบอย่างน้อย 1 ข้อก่อนเผยแพร่'},
                            status=status.HTTP_400_BAD_REQUEST)
        exam.status = Exam.Status.PUBLISHED
        exam.save(update_fields=['status'])
        return Response(ExamSerializer(exam, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='questions')
    def add_question(self, request, pk=None):
        """POST /api/v1/exams/{id}/questions/ — เพิ่มข้อสอบเข้าชุด"""
        exam       = self.get_object()
        serializer = AddQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        if ExamQuestion.objects.filter(exam=exam, question_id=data['question_id']).exists():
            return Response({'detail': 'ข้อสอบนี้อยู่ในชุดแล้ว'},
                            status=status.HTTP_400_BAD_REQUEST)

        eq = ExamQuestion.objects.create(
            exam=exam,
            question_id=data['question_id'],
            score=data.get('score'),
            order_index=data.get('order_index', exam.exam_questions.count()),
        )
        return Response({'id': eq.id, 'question': eq.question_id, 'order_index': eq.order_index},
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete'], url_path='questions/(?P<qid>[^/.]+)')
    def remove_question(self, request, pk=None, qid=None):
        """DELETE /api/v1/exams/{id}/questions/{qid}/ — ลบข้อสอบออกจากชุด"""
        exam = self.get_object()
        deleted, _ = ExamQuestion.objects.filter(exam=exam, question_id=qid).delete()
        if not deleted:
            return Response({'detail': 'ไม่พบข้อสอบนี้ในชุด'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='questions/random')
    @transaction.atomic
    def add_random_questions(self, request, pk=None):
        """POST /api/v1/exams/{id}/questions/random/ — สุ่มข้อสอบเข้าชุด"""
        exam       = self.get_object()
        serializer = RandomQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subject_id = data.get('subject_id') or (exam.subject_id if exam.subject_id else None)
        if not subject_id:
            return Response({'detail': 'ต้องระบุ subject_id หรือชุดข้อสอบต้องมีวิชา'},
                            status=status.HTTP_400_BAD_REQUEST)

        existing_ids = set(exam.exam_questions.values_list('question_id', flat=True))
        qs = Question.objects.filter(subject_id=subject_id, is_active=True).exclude(id__in=existing_ids)

        if topic_id := data.get('topic_id'):
            qs = qs.filter(topic_id=topic_id)
        if difficulty := data.get('difficulty'):
            qs = qs.filter(difficulty=difficulty)
        if question_type := data.get('question_type'):
            model_class = QUESTION_TYPE_MAP.get(question_type)
            if model_class:
                qs = qs.instance_of(model_class)

        count = data['count']
        total = qs.count()
        if total < count:
            return Response({'detail': f'มีข้อสอบตรงเงื่อนไขเพียง {total} ข้อ', 'available': total},
                            status=status.HTTP_400_BAD_REQUEST)

        selected   = list(qs.order_by('?')[:count])
        start_idx  = exam.exam_questions.count()
        created    = []
        for i, q in enumerate(selected):
            eq = ExamQuestion.objects.create(exam=exam, question=q, order_index=start_idx + i)
            created.append(eq.question_id)

        return Response({'added': len(created), 'question_ids': created},
                        status=status.HTTP_201_CREATED)

    # ── Session actions ────────────────────────────────────────────────────────

    @action(detail=True, methods=['post'], url_path='sessions',
            permission_classes=[IsAuthenticated])
    @transaction.atomic
    def start_session(self, request, pk=None):
        """POST /api/v1/exams/{id}/sessions/ — เริ่มสอบ"""
        exam = self.get_object()

        if not exam.is_available:
            return Response({'detail': 'ชุดข้อสอบนี้ยังไม่พร้อมให้สอบ'},
                            status=status.HTTP_400_BAD_REQUEST)

        # ตรวจ max_attempts
        attempt_count = ExamSession.objects.filter(exam=exam, user=request.user).count()
        if exam.max_attempts and attempt_count >= exam.max_attempts:
            return Response({'detail': f'คุณสอบครบ {exam.max_attempts} ครั้งแล้ว'},
                            status=status.HTTP_400_BAD_REQUEST)

        # ตรวจ session ที่ยังค้างอยู่
        active = ExamSession.objects.filter(
            exam=exam, user=request.user, status=ExamSession.SessionStatus.IN_PROGRESS
        ).first()
        if active:
            return Response(
                ExamSessionSerializer(active, context={'request': request}).data
            )

        # สร้าง question_order
        exam_questions = list(exam.exam_questions.values_list('question_id', flat=True).order_by('order_index'))
        if exam.shuffle_questions:
            random.shuffle(exam_questions)

        # คำนวณ expires_at
        expires_at = None
        if exam.time_limit_min:
            expires_at = timezone.now() + timezone.timedelta(minutes=exam.time_limit_min)

        session = ExamSession.objects.create(
            exam           = exam,
            user           = request.user,
            attempt_number = attempt_count + 1,
            expires_at     = expires_at,
            question_order = exam_questions,
        )

        return Response(
            ExamSessionSerializer(session, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='sessions',
            permission_classes=[IsTeacherOrAdmin])
    def list_sessions(self, request, pk=None):
        """GET /api/v1/exams/{id}/sessions/ — ดูผลสอบทุก session (Teacher/Admin)"""
        exam     = self.get_object()
        sessions = exam.sessions.select_related('user').order_by('-started_at')
        return Response(ExamSessionListSerializer(sessions, many=True).data)


# =============================================================================
# ExamSessionViewSet
# =============================================================================

class ExamSessionViewSet(viewsets.GenericViewSet):
    """
    จัดการ session การสอบ

    GET    /api/v1/sessions/{id}/             — ดูข้อสอบใน session
    PATCH  /api/v1/sessions/{id}/answers/{qid}/ — บันทึกคำตอบ (auto-save)
    POST   /api/v1/sessions/{id}/submit/      — ส่งข้อสอบ
    GET    /api/v1/sessions/{id}/result/      — ดูผลสอบ
    PATCH  /api/v1/sessions/{id}/answers/{qid}/grade/ — ตรวจอัตนัย (Teacher)
    """

    queryset           = ExamSession.objects.select_related('exam', 'user').all()
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        # student เห็นเฉพาะ session ของตัวเอง
        if self.request.user.role == 'student' and obj.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        return obj

    def retrieve(self, request, pk=None):
        """GET /api/v1/sessions/{id}/ — ดึงข้อสอบใน session"""
        session = self.get_object()

        # ตรวจ expired
        if session.status == ExamSession.SessionStatus.IN_PROGRESS and session.is_expired:
            session.status = ExamSession.SessionStatus.EXPIRED
            session.save(update_fields=['status'])

        return Response(ExamSessionSerializer(session, context={'request': request}).data)

    @action(detail=True, methods=['patch'], url_path='answers/(?P<qid>[^/.]+)')
    def save_answer(self, request, pk=None, qid=None):
        """PATCH /api/v1/sessions/{id}/answers/{qid}/ — auto-save คำตอบทีละข้อ"""
        session = self.get_object()

        if session.status != ExamSession.SessionStatus.IN_PROGRESS:
            return Response({'detail': 'session นี้ไม่ได้อยู่ในสถานะกำลังสอบ'},
                            status=status.HTTP_400_BAD_REQUEST)
        if session.is_expired:
            session.status = ExamSession.SessionStatus.EXPIRED
            session.save(update_fields=['status'])
            return Response({'detail': 'หมดเวลาแล้ว'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            question = Question.objects.get(id=qid)
        except Question.DoesNotExist:
            return Response({'detail': 'ไม่พบข้อสอบ'}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        answer, _ = ExamAnswer.objects.get_or_create(session=session, question=question)
        if data.get('answer_choice'):
            answer.answer_choice_id = data['answer_choice']
        if data.get('answer_choices'):
            answer.answer_choices.set(data['answer_choices'])
        if 'answer_text' in data:
            answer.answer_text = data['answer_text']
        if 'answer_boolean' in data:
            answer.answer_boolean = data['answer_boolean']
        if data.get('answer_matching'):
            answer.answer_matching = data['answer_matching']
        answer.save()

        return Response({'detail': 'บันทึกคำตอบแล้ว', 'question_id': int(qid)})

    @action(detail=True, methods=['post'], url_path='submit')
    @transaction.atomic
    def submit(self, request, pk=None):
        """POST /api/v1/sessions/{id}/submit/ — ส่งข้อสอบ"""
        session = self.get_object()

        if session.status != ExamSession.SessionStatus.IN_PROGRESS:
            return Response({'detail': 'session นี้ส่งแล้วหรือหมดเวลา'},
                            status=status.HTTP_400_BAD_REQUEST)

        session.status       = ExamSession.SessionStatus.SUBMITTED
        session.submitted_at = timezone.now()
        session.save(update_fields=['status', 'submitted_at'])

        # ตรวจอัตโนมัติทุกคำตอบที่ตรวจได้
        for answer in session.answers.all():
            answer.auto_grade()

        # คำนวณคะแนนรวม (เฉพาะที่ตรวจแล้ว)
        session.calculate_score()
        session.refresh_from_db()

        # ตรวจครบหมดแล้ว → GRADED
        pending = session.answers.filter(is_correct__isnull=True).count()
        if pending == 0:
            session.status = ExamSession.SessionStatus.GRADED
            session.save(update_fields=['status'])

        return Response(SessionResultSerializer(session, context={'request': request}).data)

    @action(detail=True, methods=['get'], url_path='result')
    def result(self, request, pk=None):
        """GET /api/v1/sessions/{id}/result/ — ดูผลสอบ"""
        session = self.get_object()

        if session.status == ExamSession.SessionStatus.IN_PROGRESS:
            return Response({'detail': 'ยังไม่ได้ส่งข้อสอบ'},
                            status=status.HTTP_400_BAD_REQUEST)

        show = session.exam.show_result
        if show == Exam.ShowResult.NEVER:
            return Response({'detail': 'ชุดข้อสอบนี้ไม่แสดงผล'})
        if show == Exam.ShowResult.MANUAL and request.user.role == 'student':
            return Response({'detail': 'รอครูเปิดเผยผลสอบ'})

        return Response(SessionResultSerializer(session, context={'request': request}).data)

    @action(detail=True, methods=['patch'],
            url_path='answers/(?P<qid>[^/.]+)/grade',
            permission_classes=[IsTeacherOrAdmin])
    def grade_answer(self, request, pk=None, qid=None):
        """PATCH /api/v1/sessions/{id}/answers/{qid}/grade/ — ตรวจอัตนัย (Teacher)"""
        session = self.get_object()

        try:
            answer = session.answers.get(question_id=qid)
        except ExamAnswer.DoesNotExist:
            return Response({'detail': 'ไม่พบคำตอบ'}, status=status.HTTP_404_NOT_FOUND)

        serializer = GradeAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        answer.score_earned = serializer.validated_data['score_earned']
        answer.feedback     = serializer.validated_data.get('feedback', '')
        answer.graded_by    = request.user
        answer.graded_at    = timezone.now()
        answer.is_correct   = answer.score_earned > 0
        answer.save()

        # อัปเดตคะแนนรวม session
        session.calculate_score()

        # ถ้าตรวจครบแล้ว → GRADED
        pending = session.answers.filter(is_correct__isnull=True).count()
        if pending == 0:
            session.status = ExamSession.SessionStatus.GRADED
            session.save(update_fields=['status'])

        return Response({'detail': 'บันทึกการตรวจแล้ว', 'score_earned': str(answer.score_earned)})
