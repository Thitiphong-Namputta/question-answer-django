from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Subject(models.Model):
    """วิชา เช่น คณิตศาสตร์, ฟิสิกส์, ภาษาอังกฤษ"""

    name_th     = models.CharField(max_length=200, verbose_name=_('ชื่อวิชา (ไทย)'))
    name_en     = models.CharField(max_length=200, blank=True, verbose_name=_('ชื่อวิชา (อังกฤษ)'))
    code        = models.CharField(max_length=50, unique=True, blank=True, verbose_name=_('รหัสวิชา'))
    description = models.TextField(blank=True, verbose_name=_('คำอธิบาย'))
    color       = models.CharField(max_length=7, default='#4F86C6', verbose_name=_('สี (Hex)'))
    is_active   = models.BooleanField(default=True, verbose_name=_('เปิดใช้งาน'))
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_subjects',
        verbose_name=_('สร้างโดย'),
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('วิชา')
        verbose_name_plural = _('วิชา')
        ordering            = ['name_th']

    def __str__(self):
        return f'{self.name_th} ({self.code})' if self.code else self.name_th


class Topic(models.Model):
    """
    หัวข้อ/บท ภายในวิชา รองรับ nested topics (หัวข้อย่อย)
    เช่น คณิตศาสตร์ → พีชคณิต → สมการกำลังสอง
    """

    subject     = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='topics',
        verbose_name=_('วิชา'),
    )
    parent      = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('หัวข้อแม่'),
    )
    name_th     = models.CharField(max_length=200, verbose_name=_('ชื่อหัวข้อ (ไทย)'))
    name_en     = models.CharField(max_length=200, blank=True, verbose_name=_('ชื่อหัวข้อ (อังกฤษ)'))
    order_index = models.PositiveSmallIntegerField(default=0, verbose_name=_('ลำดับ'))
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('หัวข้อ')
        verbose_name_plural = _('หัวข้อ')
        ordering            = ['subject', 'order_index', 'name_th']
        unique_together     = [('subject', 'parent', 'name_th')]

    def __str__(self):
        if self.parent:
            return f'{self.subject.name_th} → {self.parent.name_th} → {self.name_th}'
        return f'{self.subject.name_th} → {self.name_th}'

    def get_depth(self):
        """คำนวณระดับความลึกของ topic (0 = root)"""
        depth, node = 0, self
        while node.parent_id:
            depth += 1
            node = node.parent
        return depth
