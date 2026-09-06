from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from story.models import Choice
from story.tests.factories import build_published_story

User = get_user_model()


class StoryApiTests(APITestCase):
    def setUp(self):
        self.ctx = build_published_story()
        self.user = User.objects.create_user(username="reader1", password="a-strong-test-password-1")
        self.client.force_authenticate(user=self.user)

    def test_unauthenticated_request_is_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/stories/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_library_lists_only_published_stories(self):
        self.ctx["story"].status = self.ctx["story"].Status.DRAFT
        self.ctx["story"].save()
        response = self.client.get("/api/stories/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_current_session_creates_run_one_at_root_node(self):
        url = f"/api/stories/{self.ctx['story'].id}/session/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["slug"], "opening")
        choice_texts = {c["display_text"] for c in response.json()["choices"]}
        self.assertEqual(choice_texts, {"She is avoiding him", "Something she remembers"})

    def test_submit_choice_advances_and_returns_profile(self):
        self.client.get(f"/api/stories/{self.ctx['story'].id}/session/")
        response = self.client.post(
            f"/api/stories/{self.ctx['story'].id}/session/choice/",
            {"choice_id": str(self.ctx["choice_reject"].id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["profile"]["profile"], {"rejection_assumption": 3})
        self.assertTrue(response.json()["profile"]["is_completed"])
        self.assertEqual(response.json()["node"]["slug"], "reads-rejection")

    def test_submitting_a_choice_not_from_current_node_is_rejected(self):
        self.client.get(f"/api/stories/{self.ctx['story'].id}/session/")
        # Advance to an ending first...
        self.client.post(
            f"/api/stories/{self.ctx['story'].id}/session/choice/",
            {"choice_id": str(self.ctx["choice_reject"].id)},
            format="json",
        )
        # ...then trying to submit again should fail because the run is completed.
        response = self.client.post(
            f"/api/stories/{self.ctx['story'].id}/session/choice/",
            {"choice_id": str(self.ctx["choice_curious"].id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_choice_gated_behind_flag_is_rejected_when_flag_missing(self):
        other_node = self.ctx["node_curious"]
        gated_choice = Choice.objects.create(
            source_node=self.ctx["start"],
            target_node=other_node,
            display_text="Secret path",
            requires_flag="found_the_letter",
            order_index=2,
        )
        self.client.get(f"/api/stories/{self.ctx['story'].id}/session/")
        response = self.client.post(
            f"/api/stories/{self.ctx['story'].id}/session/choice/",
            {"choice_id": str(gated_choice.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reflection_requires_completed_run(self):
        self.client.get(f"/api/stories/{self.ctx['story'].id}/session/")
        response = self.client.get(f"/api/stories/{self.ctx['story'].id}/session/reflection/")
        self.assertEqual(response.status_code, 400)

    def test_reflection_after_completion_returns_summary(self):
        self.client.get(f"/api/stories/{self.ctx['story'].id}/session/")
        self.client.post(
            f"/api/stories/{self.ctx['story'].id}/session/choice/",
            {"choice_id": str(self.ctx["choice_reject"].id)},
            format="json",
        )
        response = self.client.get(f"/api/stories/{self.ctx['story'].id}/session/reflection/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("rejection", response.json()["summary_text"].lower())
        self.assertEqual(len(response.json()["interpretations"]), 1)

    def test_replay_and_compare_runs(self):
        story_id = self.ctx["story"].id
        self.client.get(f"/api/stories/{story_id}/session/")
        self.client.post(
            f"/api/stories/{story_id}/session/choice/",
            {"choice_id": str(self.ctx["choice_reject"].id)},
            format="json",
        )

        replay_response = self.client.post(f"/api/stories/{story_id}/replay/", {}, format="json")
        self.assertEqual(replay_response.status_code, 200)
        self.assertEqual(replay_response.json()["run_number"], 2)

        self.client.post(
            f"/api/stories/{story_id}/session/choice/",
            {"choice_id": str(self.ctx["choice_curious"].id)},
            format="json",
        )

        compare_response = self.client.get(f"/api/stories/{story_id}/compare/", {"a": 1, "b": 2})
        self.assertEqual(compare_response.status_code, 200)
        body = compare_response.json()
        self.assertEqual(body["profile_a"], {"rejection_assumption": 3})
        self.assertEqual(body["profile_b"], {})
        self.assertEqual(len(body["diverging_choices"]), 1)

    def test_healthz_does_not_require_auth(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_error_responses_have_consistent_shape(self):
        response = self.client.get(f"/api/stories/{self.ctx['story'].id}/session/reflection/")
        # No session yet, and not completed -> this specific view raises ValidationError.
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertIn("error", body)
        self.assertIn("code", body["error"])
        self.assertIn("message", body["error"])
