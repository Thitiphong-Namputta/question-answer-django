from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from polymorphic.models import PolymorphicModel

from apps.subjects.models import Subject, Topic
from apps.questions.managers import QuestionManager


# =============================================================================
# Base Question (Polymorphic)
# =============================================================================

class Question(PolymorphicModel):
    """
    Base class สำหรับข้อสอบทุกประเภท ใช้ django-polymorphic
    เมื่อ query Question.objects.all() จะได้ instance ที่ถูกต้องของแต่ละ subclass

    Subclasses:
      - MultipleChoiceQuestion  (ปรนัย)
      - EssayQuestion           (อัตนัย)
      - TrueFalseQuestion       (ถูก/ผิด)
      - FillInBlankQuestion     (เติมคำ)
      - MatchingQuestion        (จับคู่)
    """

    class Difficulty(models.TextChoices):
        EASY   = 'easy',   _('ง่าย')
        MEDIUM = 'medium', _('ปานกลาง')
        HARD   = 'hard',   _('ยาก')

    # ── ข้อมูลหลัก ────────────────────────────────────────────────────────────
    subject    = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name='questions',
        verbose_name=_('วิชา'),
    )
    topic      = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='questions',
        verbose_name=_('หัวข้อ'),
    )
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty,
        default=Difficulty.MEDIUM,
        verbose_name=_('ระดับความยาก'),
    )

    # ── เนื้อหาโจทย์ (รองรับ 2 ภาษา + LaTeX + รูปภาพ) ──────────────────────────
    body_th    = models.TextField(verbose_name=_('โจทย์ (ไทย)'))
    body_en    = models.TextField(blank=True, verbose_name=_('โจทย์ (อังกฤษ)'))
    body_latex = models.TextField(blank=True, verbose_name=_('สูตร LaTeX'))
    image      = models.ImageField(
        upload_to='questions/images/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('รูปภาพประกอบ'),
    )

    # ── เฉลย/อธิบาย ──────────────────────────────────────────────────────────
    explanation_th    = models.TextField(blank=True, verbose_name=_('เฉลย/อธิบาย (ไทย)'))
    explanation_en    = models.TextField(blank=True, verbose_name=_('เฉลย/อธิบาย (อังกฤษ)'))
    explanation_latex = models.TextField(blank=True, verbose_name=_('สูตร LaTeX เฉลย'))
    explanation_image = models.ImageField(
        upload_to='questions/explanations/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('รูปภาพประกอบเฉลย'),
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    score      = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0)],
        verbose_name=_('คะแนนเต็ม'),
    )
    # JSONField ใช้แทน ArrayField เพื่อรองรับ SQLite ใน dev
    # ตัวอย่าง: ["พีชคณิต", "วงกลม"]
    tags       = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('แท็ก'),
    )
    source     = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('แหล่งที่มา'),
        help_text=_('เช่น PAT1 2566, สอบกลางภาค 1/2567'),
    )
    is_active  = models.BooleanField(default=True, verbose_name=_('เปิดใช้งาน'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_questions',
        verbose_name=_('สร้างโดย'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = QuestionManager()

    class Meta:
        verbose_name        = _('ข้อสอบ')
        verbose_name_plural = _('ข้อสอบ')
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['subject', 'difficulty']),
            models.Index(fields=['subject', 'topic']),
            models.Index(fields=['is_active', 'created_at']),
        ]

    def __str__(self):
        preview = self.body_th[:60] + '...' if len(self.body_th) > 60 else self.body_th
        return f'[{self.get_question_type_label()}] {preview}'

    def get_question_type_label(self):
        return 'ข้อสอบ'


# =============================================================================
# 1. ปรนัย (Multiple Choice)
# =============================================================================

class MultipleChoiceQuestion(Question):
    """ข้อสอบปรนัย รองรับทั้งคำตอบเดียว (single) และหลายคำตอบ (multiple)"""

    class AnswerMode(models.TextChoices):
        SINGLE   = 'single',   _('คำตอบเดียว')
        MULTIPLE = 'multiple', _('หลายคำตอบ')

    answer_mode = models.CharField(
        max_length=10,
        choices=AnswerMode,
        default=AnswerMode.SINGLE,
        verbose_name=_('รูปแบบคำตอบ'),
    )

    class Meta:
        verbose_name        = _('ข้อสอบปรนัย')
        verbose_name_plural = _('ข้อสอบปรนัย')

    def get_question_type_label(self):
        return 'ปรนัย'

    def get_correct_choices(self):
        return self.choices.filter(is_correct=True)


class Choice(models.Model):
    """ตัวเลือกของข้อสอบปรนัย"""

    question    = models.ForeignKey(
        MultipleChoiceQuestion,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name=_('ข้อสอบ'),
    )
    label       = models.CharField(max_length=5, verbose_name=_('ตัวอักษร (A, B, C, D)'))
    body_th     = models.TextField(verbose_name=_('ตัวเลือก (ไทย)'))
    body_en     = models.TextField(blank=True, verbose_name=_('ตัวเลือก (อังกฤษ)'))
    body_latex  = models.TextField(blank=True, verbose_name=_('LaTeX'))
    image       = models.ImageField(
        upload_to='questions/choices/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('รูปภาพ'),
    )
    is_correct  = models.BooleanField(default=False, verbose_name=_('เป็นคำตอบที่ถูก'))
    order_index = models.PositiveSmallIntegerField(default=0, verbose_name=_('ลำดับ'))

    class Meta:
        verbose_name        = _('ตัวเลือก')
        verbose_name_plural = _('ตัวเลือก')
        ordering            = ['order_index', 'label']
        unique_together     = [('question', 'label')]

    def __str__(self):
        return f'{self.label}. {self.body_th[:40]}'


# =============================================================================
# 2. อัตนัย (Essay)
# =============================================================================

class EssayQuestion(Question):
    """ข้อสอบอัตนัย ผู้สอบพิมพ์คำตอบเป็น text ต้องให้ครูตรวจ (manual grading)"""

    sample_answer  = models.TextField(
        blank=True,
        verbose_name=_('เฉลยตัวอย่าง'),
        help_text=_('คำตอบตัวอย่างสำหรับครูใช้ในการตรวจ'),
    )
    max_words      = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('จำนวนคำสูงสุด'),
    )
    grading_rubric = models.TextField(
        blank=True,
        verbose_name=_('เกณฑ์การให้คะแนน (Rubric)'),
    )

    class Meta:
        verbose_name        = _('ข้อสอบอัตนัย')
        verbose_name_plural = _('ข้อสอบอัตนัย')

    def get_question_type_label(self):
        return 'อัตนัย'


# =============================================================================
# 3. ถูก/ผิด (True/False)
# =============================================================================

class TrueFalseQuestion(Question):
    """ข้อสอบถูก/ผิด ตรวจได้อัตโนมัติ"""

    correct_answer = models.BooleanField(
        verbose_name=_('คำตอบที่ถูก'),
        help_text=_('True = ถูก, False = ผิด'),
    )
    true_label  = models.CharField(max_length=50, default='ถูก', verbose_name=_('ข้อความแทน "ถูก"'))
    false_label = models.CharField(max_length=50, default='ผิด', verbose_name=_('ข้อความแทน "ผิด"'))

    class Meta:
        verbose_name        = _('ข้อสอบถูก/ผิด')
        verbose_name_plural = _('ข้อสอบถูก/ผิด')

    def get_question_type_label(self):
        return 'ถูก/ผิด'


# =============================================================================
# 4. เติมคำ (Fill in the Blank)
# =============================================================================

class FillInBlankQuestion(Question):
    """
    ข้อสอบเติมคำ รองรับหลายช่อง (blank)
    ใช้ {{1}}, {{2}}, ... แทนช่องว่างในโจทย์

    ตัวอย่าง body_th: "กรุงเทพฯ เป็นเมืองหลวงของ {{1}} และมีประชากรประมาณ {{2}} ล้านคน"
    """

    class GradingMode(models.TextChoices):
        EXACT       = 'exact',       _('ตรงทุกตัวอักษร')
        IGNORE_CASE = 'ignore_case', _('ไม่สนตัวพิมพ์เล็ก/ใหญ่')
        CONTAINS    = 'contains',    _('มีคำที่อยู่ในคำตอบ')

    grading_mode = models.CharField(
        max_length=15,
        choices=GradingMode,
        default=GradingMode.IGNORE_CASE,
        verbose_name=_('วิธีตรวจคำตอบ'),
    )

    class Meta:
        verbose_name        = _('ข้อสอบเติมคำ')
        verbose_name_plural = _('ข้อสอบเติมคำ')

    def get_question_type_label(self):
        return 'เติมคำ'

    def get_blank_count(self):
        """นับจำนวนช่องว่างจาก pattern {{N}}"""
        import re
        return len(re.findall(r'\{\{\d+\}\}', self.body_th))


class BlankAnswer(models.Model):
    """คำตอบที่ถูกต้องสำหรับแต่ละช่องว่าง รองรับหลายคำตอบต่อหนึ่งช่อง"""

    question     = models.ForeignKey(
        FillInBlankQuestion,
        on_delete=models.CASCADE,
        related_name='blank_answers',
        verbose_name=_('ข้อสอบ'),
    )
    blank_number = models.PositiveSmallIntegerField(
        verbose_name=_('ช่องที่'),
        help_text=_('ตามหมายเลขใน {{N}}'),
    )
    answer_text  = models.CharField(max_length=200, verbose_name=_('คำตอบที่ถูก'))
    order_index  = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('ลำดับ (ถ้ามีหลายคำตอบ)'),
    )

    class Meta:
        verbose_name        = _('คำตอบช่องว่าง')
        verbose_name_plural = _('คำตอบช่องว่าง')
        ordering            = ['blank_number', 'order_index']

    def __str__(self):
        return f'ช่องที่ {self.blank_number}: {self.answer_text}'


# =============================================================================
# 5. จับคู่ (Matching)
# =============================================================================

class MatchingQuestion(Question):
    """
    ข้อสอบจับคู่ — แสดงคอลัมน์ซ้าย (ถาม) และขวา (ตอบ) ให้จับคู่กัน
    สามารถสุ่มลำดับตัวเลือกขวาได้
    """

    shuffle_right = models.BooleanField(
        default=True,
        verbose_name=_('สุ่มลำดับคอลัมน์ขวา'),
    )

    class Meta:
        verbose_name        = _('ข้อสอบจับคู่')
        verbose_name_plural = _('ข้อสอบจับคู่')

    def get_question_type_label(self):
        return 'จับคู่'


class MatchingPair(models.Model):
    """คู่จับคู่ของข้อสอบจับคู่"""

    question    = models.ForeignKey(
        MatchingQuestion,
        on_delete=models.CASCADE,
        related_name='pairs',
        verbose_name=_('ข้อสอบ'),
    )
    # คอลัมน์ซ้าย (ถาม)
    left_body   = models.TextField(verbose_name=_('คอลัมน์ซ้าย (ถาม)'))
    left_image  = models.ImageField(
        upload_to='questions/matching/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('รูปภาพคอลัมน์ซ้าย'),
    )
    # คอลัมน์ขวา (ตอบ)
    right_body  = models.TextField(verbose_name=_('คอลัมน์ขวา (ตอบ)'))
    right_image = models.ImageField(
        upload_to='questions/matching/%Y/%m/',
        blank=True,
        null=True,
        verbose_name=_('รูปภาพคอลัมน์ขวา'),
    )
    order_index = models.PositiveSmallIntegerField(default=0, verbose_name=_('ลำดับ'))

    class Meta:
        verbose_name        = _('คู่จับคู่')
        verbose_name_plural = _('คู่จับคู่')
        ordering            = ['order_index']

    def __str__(self):
        return f'{self.left_body[:30]} ↔ {self.right_body[:30]}'
