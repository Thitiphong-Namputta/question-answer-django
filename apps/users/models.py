from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom User Model — แทน default User ของ Django
    ตั้งค่า AUTH_USER_MODEL = 'users.User' ใน settings.py
    """

    class Role(models.TextChoices):
        ADMIN   = 'admin',   _('ผู้ดูแลระบบ')
        TEACHER = 'teacher', _('อาจารย์/ผู้ออกข้อสอบ')
        STUDENT = 'student', _('นักเรียน/ผู้สอบ')

    class Locale(models.TextChoices):
        TH = 'th', _('ภาษาไทย')
        EN = 'en', _('English')

    role       = models.CharField(max_length=20, choices=Role, default=Role.STUDENT, verbose_name=_('บทบาท'))
    avatar_url = models.URLField(blank=True, verbose_name=_('รูปโปรไฟล์'))
    locale     = models.CharField(max_length=5, choices=Locale, default=Locale.TH, verbose_name=_('ภาษา'))
    bio        = models.TextField(blank=True, verbose_name=_('เกี่ยวกับ'))

    class Meta:
        verbose_name        = _('ผู้ใช้งาน')
        verbose_name_plural = _('ผู้ใช้งาน')
        ordering            = ['username']

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT
