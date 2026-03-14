from rest_framework.routers import DefaultRouter

from apps.questions.views import QuestionViewSet

router = DefaultRouter()
router.register(r'questions', QuestionViewSet, basename='question')

urlpatterns = router.urls
