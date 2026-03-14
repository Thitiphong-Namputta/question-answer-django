from polymorphic.managers import PolymorphicManager
from polymorphic.query import PolymorphicQuerySet


class QuestionQuerySet(PolymorphicQuerySet):

    def active(self):
        return self.filter(is_active=True)

    def by_subject(self, subject_id):
        return self.filter(subject_id=subject_id)

    def by_topic(self, topic_id):
        return self.filter(topic_id=topic_id)

    def by_difficulty(self, difficulty):
        return self.filter(difficulty=difficulty)

    def by_tags(self, *tags):
        """กรองข้อสอบที่มี tag ใดก็ได้จาก tags ที่ระบุ"""
        from django.db.models import Q
        q = Q()
        for tag in tags:
            q |= Q(tags__contains=tag)
        return self.filter(q)

    def random(self, count):
        """สุ่มข้อสอบจำนวน count ข้อ"""
        return self.order_by('?')[:count]

    def multiple_choice(self):
        from apps.questions.models import MultipleChoiceQuestion
        return self.instance_of(MultipleChoiceQuestion)

    def essay(self):
        from apps.questions.models import EssayQuestion
        return self.instance_of(EssayQuestion)

    def true_false(self):
        from apps.questions.models import TrueFalseQuestion
        return self.instance_of(TrueFalseQuestion)

    def fill_in_blank(self):
        from apps.questions.models import FillInBlankQuestion
        return self.instance_of(FillInBlankQuestion)

    def matching(self):
        from apps.questions.models import MatchingQuestion
        return self.instance_of(MatchingQuestion)


class QuestionManager(PolymorphicManager):
    queryset_class = QuestionQuerySet

    def active(self):
        return self.get_queryset().active()
