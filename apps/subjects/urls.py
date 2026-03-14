from rest_framework.routers import DefaultRouter

from apps.subjects.views import SubjectViewSet, TopicViewSet

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'topics',   TopicViewSet,   basename='topic')

urlpatterns = router.urls
