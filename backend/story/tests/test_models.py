from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from story.models import Choice, ChoiceTagWeight, PsychologicalTag, ReadingSession, StoryNode, StoryVersion
from story.tests.factories import build_published_story

User = get_user_model()


class StoryVersionGraphValidationTests(TestCase):
    def test_well_formed_graph_has_no_problems(self):
        ctx = build_published_story()
        self.assertEqual(ctx["version"].validate_graph(), [])

    def test_unreachable_node_is_flagged(self):
        ctx = build_published_story()
        orphan = StoryNode.objects.create(
            story_version=ctx["version"],
            chapter_title="Ch1",
            slug="orphan",
            text_content="Nobody can reach this.",
        )
        problems = ctx["version"].validate_graph()
        self.assertTrue(any(str(orphan.id) in p for p in problems))

    def test_dead_end_not_marked_ending_is_flagged(self):
        ctx = build_published_story()
        dead_end = StoryNode.objects.create(
            story_version=ctx["version"],
            chapter_title="Ch1",
            slug="dead-end",
            text_content="This goes nowhere.",
            node_type=StoryNode.NodeType.STANDARD,
        )
        Choice.objects.create(
            source_node=ctx["start"], target_node=dead_end, display_text="Go nowhere", order_index=2
        )
        problems = ctx["version"].validate_graph()
        self.assertTrue(any("dead-end" in p for p in problems))

    def test_publish_without_root_node_raises(self):
        ctx = build_published_story()
        version = StoryVersion.objects.create(story=ctx["story"], version_number=2)
        with self.assertRaises(ValidationError):
            version.publish()


class ChoiceIntegrityTests(TestCase):
    def test_self_loop_choice_is_rejected_at_db_level(self):
        ctx = build_published_story()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Choice.objects.create(
                    source_node=ctx["start"], target_node=ctx["start"], display_text="Loop"
                )

    def test_choice_across_story_versions_fails_clean(self):
        ctx = build_published_story()
        other = build_published_story(slug="other-story", title="Other Story")
        bad_choice = Choice(
            source_node=ctx["start"], target_node=other["node_curious"], display_text="Cross-version"
        )
        with self.assertRaises(ValidationError):
            bad_choice.clean()


class ReadingSessionTests(TestCase):
    def setUp(self):
        self.ctx = build_published_story()
        self.user = User.objects.create_user(username="reader1", password="a-strong-test-password-1")

    def test_apply_choice_updates_profile_and_completes_on_ending(self):
        session = ReadingSession.objects.create(
            user=self.user, story_version=self.ctx["version"], run_number=1, current_node=self.ctx["start"]
        )
        session.apply_choice(self.ctx["choice_reject"])

        self.assertEqual(session.psychological_profile, {"rejection_assumption": 3})
        self.assertTrue(session.is_completed)
        self.assertEqual(session.current_node_id, self.ctx["node_reject"].id)
        self.assertEqual(session.interpretations.count(), 1)
        self.assertEqual(session.choice_history.count(), 1)

    def test_choice_with_no_tags_leaves_profile_empty(self):
        session = ReadingSession.objects.create(
            user=self.user, story_version=self.ctx["version"], run_number=1, current_node=self.ctx["start"]
        )
        session.apply_choice(self.ctx["choice_curious"])
        self.assertEqual(session.psychological_profile, {})

    def test_second_run_for_same_user_and_version_requires_distinct_run_number(self):
        ReadingSession.objects.create(
            user=self.user, story_version=self.ctx["version"], run_number=1
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReadingSession.objects.create(
                    user=self.user, story_version=self.ctx["version"], run_number=1
                )
        # A different run_number for the same user+version is fine (replay).
        ReadingSession.objects.create(
            user=self.user, story_version=self.ctx["version"], run_number=2
        )
