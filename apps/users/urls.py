from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from apps.users import views

urlpatterns = [
    # JWT Auth
    path('auth/login/',   TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(),    name='token_refresh'),
    path('auth/verify/',  TokenVerifyView.as_view(),     name='token_verify'),

    # Profile
    path('auth/me/',              views.MeView.as_view(),   name='me'),
    path('auth/change-password/', views.change_password,    name='change_password'),

    # User management (Admin)
    path('users/',              views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/role/', views.change_user_role,      name='change_user_role'),
]
