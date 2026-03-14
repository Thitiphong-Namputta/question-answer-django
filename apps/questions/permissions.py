from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsTeacherOrAdmin(BasePermission):
    """เฉพาะ teacher และ admin เข้าถึงได้ (สำหรับ write operations)"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in ('teacher', 'admin')


class IsAdminOnly(BasePermission):
    """เฉพาะ admin เข้าถึงได้"""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsOwnerOrTeacherOrAdmin(BasePermission):
    """
    Object-level permission:
    - admin  → ทำได้ทุกอย่าง
    - teacher → แก้ไขได้เฉพาะของตัวเอง
    - student → อ่านได้อย่างเดียว
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user.role == 'admin':
            return True
        if request.user.role == 'teacher':
            return getattr(obj, 'created_by_id', None) == request.user.id
        return False
