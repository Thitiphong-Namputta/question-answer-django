from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.subjects.models import Subject
from apps.questions.models import Question, Choice


# =============================================================================
# Exam — ชุดข้อสอบ
# =============================================================================

class Exam(models.Model):
    """ชุดข้อสอบ สร้างโดยครู/admin ประกอบด้วยข้อสอบหลายข้อ"""

    class Status(models.TextChoices):
        DRAFT     = 'draft',     _('ร่าง')
        PUBLISHED = 'published', _('เผยแพร่')
        ARCHIVED  = 'archived',  _('เก็บถาวร')

    class ShowResult(models.TextChoices):
        IMMEDIATELY  = 'immediately',  _('แสดงทันทีหลังตอบแต่ละข้อ')
        AFTER_SUBMIT = 'after_submit', _('แสดงหลังส่งข้อสอบ')
        MANUAL       = 'manual',       _('ครูเปิดเผยเอง')
        NEVER        = 'never',        _('ไม่แสดง')

    title_th    = models.CharField(max_length=300, verbose_name=_('ชื่อชุดข้อสอบ (ไทย)'))
    title_en    = models.CharField(max_length=300, blank=True, verbose_name=_('ชื่อชุดข้อสอบ (อังกฤษ)'))
    description = models.TextField(blank=True, verbose_name=_('คำอธิบาย'))
    subject     = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exams',
        verbose_name=_('วิชา'),
    )

    # ── การตั้งค่า ────────────────────────────────────────────────────────────
    time_limit_min    = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_('เวลาจำกัด (นาที)'),
        help_text=_('ว่างไว้ = ไม่จำกัดเวลา'),
    )
    total_score       = models.DecimalField(
        max_digits=7, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('คะแนนเต็มรวม'),
    )
    pass_score        = models.DecimalField(
        max_digits=7, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('คะแนนผ่าน'),
    )
    shuffle_questions = models.BooleanField(default=False, verbose_name=_('สุ่มลำดับข้อสอบ'))
    shuffle_choices   = models.BooleanField(default=False, verbose_name=_('สุ่มลำดับตัวเลือก'))
    show_result       = models.CharField(
        max_length=20,
        choices=ShowResult,
        default=ShowResult.AFTER_SUBMIT,
        verbose_name=_('การแสดงผลลัพธ์'),
    )
    max_attempts      = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_('จำนวนครั้งที่สอบได้'),
        help_text=_('ว่างไว้ = ไม่จำกัด'),
    )

    # ── ช่วงเวลา ──────────────────────────────────────────────────────────────
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name=_('เริ่มสอบ'))
    ends_at   = models.DateTimeField(null=True, blank=True, verbose_name=_('สิ้นสุด'))

    status     = models.CharField(max_length=20, choices=Status, default=Status.DRAFT, verbose_name=_('สถานะ'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_exams',
        verbose_name=_('สร้างโดย'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('ชุดข้อสอบ')
        verbose_name_plural = _('ชุดข้อสอบ')
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'starts_at']),
            models.Index(fields=['subject', 'status']),
        ]

    def __str__(self):
        return self.title_th

    @property
    def is_available(self):
        """ตรวจสอบว่าชุดข้อสอบพร้อมให้สอบหรือยัง"""
        if self.status != self.Status.PUBLISHED:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def get_total_score(self):
        """คำนวณคะแนนรวมจากข้อสอบทั้งหมดในชุด"""
        from django.db.models import Sum
        result = self.exam_questions.aggregate(total=Sum('score'))
        return result['total'] or 0


# =============================================================================
# ExamQuestion — ข้อสอบในชุด (many-to-many)
# =============================================================================

class ExamQuestion(models.Model):
    """ข้อสอบแต่ละข้อที่อยู่ในชุดข้อสอบ พร้อม order และ score override"""

    exam        = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='exam_questions',
        verbose_name=_('ชุดข้อสอบ'),
    )
    question    = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='exam_questions',
        verbose_name=_('ข้อสอบ'),
    )
    order_index = models.PositiveSmallIntegerField(default=0, verbose_name=_('ลำดับ'))
    score       = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('คะแนน (override)'),
        help_text=_('ว่างไว้ = ใช้คะแนนจากข้อสอบต้นฉบับ'),
    )

    class Meta:
        verbose_name        = _('ข้อสอบในชุด')
        verbose_name_plural = _('ข้อสอบในชุด')
        ordering            = ['order_index']
        unique_together     = [('exam', 'question')]

    def __str__(self):
        return f'{self.exam.title_th} — ข้อ {self.order_index + 1}'

    def get_score(self):
        """คะแนนที่ใช้จริง (override หรือจาก question)"""
        return self.score if self.score is not None else self.question.score


# =============================================================================
# ExamSession — การสอบแต่ละครั้ง
# =============================================================================

class ExamSession(models.Model):
    """บันทึกการสอบของนักเรียนแต่ละครั้ง"""

    class SessionStatus(models.TextChoices):
        IN_PROGRESS = 'in_progress', _('กำลังทำข้อสอบ')
        SUBMITTED   = 'submitted',   _('ส่งแล้ว')
        EXPIRED     = 'expired',     _('หมดเวลา')
        GRADED      = 'graded',      _('ตรวจแล้ว')

    exam           = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('ชุดข้อสอบ'),
    )
    user           = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_sessions',
        verbose_name=_('ผู้สอบ'),
    )
    attempt_number = models.PositiveSmallIntegerField(default=1, verbose_name=_('ครั้งที่'))

    started_at    = models.DateTimeField(auto_now_add=True, verbose_name=_('เริ่มสอบ'))
    submitted_at  = models.DateTimeField(null=True, blank=True, verbose_name=_('ส่งข้อสอบ'))
    expires_at    = models.DateTimeField(null=True, blank=True, verbose_name=_('หมดเวลา'))

    status        = models.CharField(
        max_length=20,
        choices=SessionStatus,
        default=SessionStatus.IN_PROGRESS,
        verbose_name=_('สถานะ'),
    )
    total_score   = models.DecimalField(
        max_digits=7, decimal_places=2,
        null=True, blank=True,
        verbose_name=_('คะแนนรวมที่ได้'),
    )
    is_passed     = models.BooleanField(null=True, blank=True, verbose_name=_('ผ่าน/ไม่ผ่าน'))

    # snapshot ลำดับข้อสอบที่สุ่มไว้ (JSON array of question IDs)
    question_order = models.JSONField(
        default=list,
        verbose_name=_('ลำดับข้อสอบ (snapshot)'),
    )

    class Meta:
        verbose_name        = _('การสอบ')
        verbose_name_plural = _('การสอบ')
        ordering            = ['-started_at']
        unique_together     = [('exam', 'user', 'attempt_number')]
        indexes = [
            models.Index(fields=['exam', 'user']),
            models.Index(fields=['status', 'started_at']),
        ]

    def __str__(self):
        return f'{self.user} — {self.exam.title_th} (ครั้งที่ {self.attempt_number})'

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def calculate_score(self):
        """คำนวณและบันทึกคะแนนรวมจากคำตอบทั้งหมด"""
        from django.db.models import Sum
        result = self.answers.aggregate(total=Sum('score_earned'))
        self.total_score = result['total'] or 0

        pass_score = self.exam.pass_score
        if pass_score is not None:
            self.is_passed = self.total_score >= pass_score

        self.save(update_fields=['total_score', 'is_passed'])
        return self.total_score


# =============================================================================
# ExamAnswer — คำตอบของผู้สอบ
# =============================================================================

class ExamAnswer(models.Model):
    """คำตอบของผู้สอบสำหรับแต่ละข้อสอบใน session"""

    session     = models.ForeignKey(
        ExamSession,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('การสอบ'),
    )
    question    = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('ข้อสอบ'),
    )

    # ── คำตอบ (ใช้ field ที่เหมาะสมตามประเภทข้อสอบ) ──────────────────────────
    answer_choice  = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('ตัวเลือกที่เลือก (ปรนัย)'),
    )
    answer_choices = models.ManyToManyField(
        Choice,
        blank=True,
        related_name='answers_multiple',
        verbose_name=_('ตัวเลือกที่เลือก (ปรนัยหลายคำตอบ)'),
    )
    answer_text    = models.TextField(
        blank=True,
        verbose_name=_('คำตอบข้อความ (อัตนัย/เติมคำ)'),
    )
    answer_boolean = models.BooleanField(
        null=True, blank=True,
        verbose_name=_('คำตอบถูก/ผิด'),
    )
    # matching: [{"left_id": 1, "right_id": 3}, ...]
    answer_matching = models.JSONField(
        null=True, blank=True,
        verbose_name=_('คำตอบจับคู่'),
    )

    # ── ผลการตรวจ ─────────────────────────────────────────────────────────────
    is_correct   = models.BooleanField(
        null=True, blank=True,
        verbose_name=_('ถูกต้อง'),
        help_text=_('None = ยังไม่ตรวจ (อัตนัย)'),
    )
    score_earned = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_('คะแนนที่ได้'),
    )
    graded_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='graded_answers',
        verbose_name=_('ตรวจโดย'),
    )
    graded_at  = models.DateTimeField(null=True, blank=True, verbose_name=_('วันที่ตรวจ'))
    feedback   = models.TextField(blank=True, verbose_name=_('ความเห็นของครู'))

    answered_at = models.DateTimeField(auto_now=True, verbose_name=_('ตอบเมื่อ'))

    class Meta:
        verbose_name        = _('คำตอบ')
        verbose_name_plural = _('คำตอบ')
        unique_together     = [('session', 'question')]
        indexes = [
            models.Index(fields=['session', 'question']),
        ]

    def __str__(self):
        return f'Session {self.session_id} — Q{self.question_id}'

    def auto_grade(self):
        """ตรวจอัตโนมัติสำหรับ MCQ, TrueFalse, FillInBlank (ไม่รวม Essay, Matching)"""
        from apps.questions.models import (
            MultipleChoiceQuestion, TrueFalseQuestion, FillInBlankQuestion
        )
        q = self.question.get_real_instance()
        exam_q = ExamQuestion.objects.filter(
            exam=self.session.exam, question=self.question
        ).first()
        max_score = exam_q.get_score() if exam_q else self.question.score

        if isinstance(q, MultipleChoiceQuestion):
            if q.answer_mode == 'single':
                correct = q.choices.filter(is_correct=True).first()
                self.is_correct = (self.answer_choice_id == correct.id) if correct else False
            else:
                correct_ids = set(q.choices.filter(is_correct=True).values_list('id', flat=True))
                selected_ids = set(self.answer_choices.values_list('id', flat=True))
                self.is_correct = correct_ids == selected_ids
            self.score_earned = max_score if self.is_correct else 0

        elif isinstance(q, TrueFalseQuestion):
            self.is_correct  = self.answer_boolean == q.correct_answer
            self.score_earned = max_score if self.is_correct else 0

        elif isinstance(q, FillInBlankQuestion):
            if self.answer_text and q.blank_answers.exists():
                # ตรวจคำตอบช่องแรก (blank_number=1) เป็น baseline
                expected = q.blank_answers.filter(blank_number=1).first()
                if expected:
                    if q.grading_mode == 'exact':
                        self.is_correct = self.answer_text == expected.answer_text
                    elif q.grading_mode == 'ignore_case':
                        self.is_correct = self.answer_text.lower() == expected.answer_text.lower()
                    else:  # contains
                        self.is_correct = expected.answer_text.lower() in self.answer_text.lower()
                    self.score_earned = max_score if self.is_correct else 0

        self.save(update_fields=['is_correct', 'score_earned'])
        return self.is_correct
