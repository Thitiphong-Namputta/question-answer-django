from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.exams.views import ExamViewSet, ExamSessionViewSet

router = DefaultRouter()
router.register(r'exams',    ExamViewSet,        basename='exam')
router.register(r'sessions', ExamSessionViewSet, basename='session')

urlpatterns = router.urls + [
    # ExamViewSet extra actions ที่ router ไม่จับ (nested URL กับ qid)
    path(
        'exams/<int:pk>/questions/<int:qid>/',
        ExamViewSet.as_view({'delete': 'remove_question'}),
        name='exam-remove-question',
    ),
]
