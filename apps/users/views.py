from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.questions.permissions import IsAdminOnly
from apps.users.models import User
from apps.users.serializers import (
    UserSerializer, UserListSerializer,
    UserRoleSerializer, ChangePasswordSerializer,
)


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/auth/me/   — ดูโปรไฟล์ตัวเอง
    PATCH /api/v1/auth/me/  — แก้ไขโปรไฟล์
    """
    serializer_class   = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """POST /api/v1/auth/change-password/"""
    serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({'detail': 'เปลี่ยนรหัสผ่านสำเร็จ'})


class UserListView(generics.ListAPIView):
    """GET /api/v1/users/ — รายการผู้ใช้ (Admin เท่านั้น)"""
    queryset           = User.objects.all().order_by('username')
    serializer_class   = UserListSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs


@api_view(['PATCH'])
@permission_classes([IsAdminOnly])
def change_user_role(request, pk):
    """PATCH /api/v1/users/{id}/role/ — เปลี่ยน role (Admin เท่านั้น)"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'detail': 'ไม่พบผู้ใช้'}, status=status.HTTP_404_NOT_FOUND)

    serializer = UserRoleSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(UserSerializer(user).data)
