from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer สำหรับดูและแก้ไขโปรไฟล์"""

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'email',
            'first_name', 'last_name',
            'role', 'locale', 'avatar_url', 'bio',
            'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'role', 'is_active', 'date_joined']


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight สำหรับ list (Admin)"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'locale', 'is_active', 'date_joined']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class UserRoleSerializer(serializers.ModelSerializer):
    """สำหรับ Admin เปลี่ยน role"""

    class Meta:
        model  = User
        fields = ['role']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({'old_password': 'รหัสผ่านเดิมไม่ถูกต้อง'})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
