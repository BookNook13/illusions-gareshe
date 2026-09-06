"""
views.py — Reader-facing story API.

  GET  /api/stories/                                  -> library / discovery
  GET  /api/stories/<story_id>/session/                -> current (or start) session's node
  POST /api/stories/<story_id>/session/choice/          -> submit a choice
  GET  /api/stories/<story_id>/session/profile/         -> psychological profile so far
  GET  /api/stories/<story_id>/session/reflection/       -> end-of-story reflection
  POST /api/stories/<story_id>/replay/                  -> start a new run (increments run_number)
  GET  /api/stories/<story_id>/compare/?a=1&b=2         -> diff two runs
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Choice, ReadingSession, Reflection, Story, StoryNode
from .serializers import (
    PsychologicalProfileSerializer,
    ReflectionSerializer,
    RunComparisonSerializer,
    StoryListSerializer,
    StoryNodeSerializer,
    SubmitChoiceSerializer,
)


def get_or_create_latest_session(user, story: Story) -> ReadingSession:
    """
    Fetches the reader's most recent (highest run_number) ReadingSession
    for this story's published version, creating run #1 at the version's
    root_node if they've never started it.
    """
    version = story.published_version
    if version is None:
        raise ValidationError("This story has no published version yet.")

    latest = (
        ReadingSession.objects.filter(user=user, story_version=version)
        .order_by("-run_number")
        .first()
    )
    if latest is not None:
        return latest

    return ReadingSession.objects.create(
        user=user, story_version=version, run_number=1, current_node=version.root_node
    )


class StoryListView(APIView):
    """Library / discovery: published stories only."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        stories = Story.objects.filter(status=Story.Status.PUBLISHED).prefetch_related("themes")
        return Response(StoryListSerializer(stories, many=True).data)


class CurrentSessionNodeView(APIView):
    """Returns the reader's current node in their latest run of this story."""

    permission_classes = [IsAuthenticated]

    def get(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        session = get_or_create_latest_session(request.user, story)

        if session.current_node is None:
            return Response(
                {"detail": "No current node set for this session."},
                status=status.HTTP_409_CONFLICT,
            )

        node = StoryNode.objects.prefetch_related("outgoing_choices").get(
            pk=session.current_node_id
        )
        return Response(StoryNodeSerializer(node, context={"session": session}).data)


class SubmitChoiceView(APIView):
    """Validates and applies a choice within the reader's latest run."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        input_serializer = SubmitChoiceSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        choice_id = input_serializer.validated_data["choice_id"]

        version = story.published_version
        if version is None:
            raise ValidationError("This story has no published version yet.")

        session = (
            ReadingSession.objects.select_for_update()
            .filter(user=request.user, story_version=version)
            .order_by("-run_number")
            .first()
        )
        if session is None:
            raise ValidationError("No active session — GET the session endpoint first.")

        if session.is_completed:
            raise ValidationError("This run has already reached an ending. Start a replay instead.")

        choice = get_object_or_404(
            Choice.objects.select_related("source_node", "target_node"), pk=choice_id
        )

        if choice.source_node_id != session.current_node_id:
            raise ValidationError("That choice is not available from the reader's current node.")

        if choice.requires_flag and choice.requires_flag not in session.flags:
            raise ValidationError("This choice is gated behind a flag the reader hasn't collected.")

        session.apply_choice(choice)

        node_serializer = StoryNodeSerializer(session.current_node, context={"session": session})
        return Response(
            {
                "node": node_serializer.data,
                "profile": PsychologicalProfileSerializer.from_session(session).data,
            }
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        session = get_or_create_latest_session(request.user, story)
        return Response(PsychologicalProfileSerializer.from_session(session).data)


class ReflectionView(APIView):
    """
    Returns the cached Reflection for the reader's latest completed run,
    generating a lightweight deterministic one on first request if none
    exists yet. The AI analysis layer (Phase 3+) can later regenerate
    summary_text with a richer model without changing this contract.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        session = get_or_create_latest_session(request.user, story)

        if not session.is_completed:
            raise ValidationError("This run hasn't reached an ending yet.")

        reflection, created = Reflection.objects.get_or_create(
            reading_session=session,
            defaults=self._build_defaults(session),
        )
        return Response(ReflectionSerializer(reflection).data)

    def _build_defaults(self, session: ReadingSession) -> dict:
        profile = session.psychological_profile
        if not profile:
            return {"summary_text": "This run didn't surface a strong recurring pattern.", "strongest_tag": None}

        strongest_slug = max(profile, key=profile.get)
        from .models import PsychologicalTag

        strongest_tag = PsychologicalTag.objects.filter(slug=strongest_slug).first()
        description = (
            strongest_tag.reader_facing_description
            if strongest_tag and strongest_tag.reader_facing_description
            else f"Your strongest recurring pattern this run was '{strongest_slug}'."
        )
        return {"summary_text": description, "strongest_tag": strongest_tag}


class ReplayView(APIView):
    """Starts a brand new run of the story's current published version."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        version = story.published_version
        if version is None:
            raise ValidationError("This story has no published version yet.")

        last_run = (
            ReadingSession.objects.select_for_update()
            .filter(user=request.user, story_version=version)
            .order_by("-run_number")
            .first()
        )
        next_run_number = (last_run.run_number + 1) if last_run else 1

        session = ReadingSession.objects.create(
            user=request.user,
            story_version=version,
            run_number=next_run_number,
            current_node=version.root_node,
        )
        node_serializer = StoryNodeSerializer(session.current_node, context={"session": session})
        return Response({"run_number": session.run_number, "node": node_serializer.data})


class RunComparisonView(APIView):
    """GET /api/stories/<story_id>/compare/?a=1&b=2 — diff two runs of the same story."""

    permission_classes = [IsAuthenticated]

    def get(self, request, story_id):
        story = get_object_or_404(Story, pk=story_id)
        version = story.published_version
        if version is None:
            raise ValidationError("This story has no published version yet.")

        try:
            run_a = int(request.query_params.get("a", ""))
            run_b = int(request.query_params.get("b", ""))
        except ValueError:
            raise ValidationError("Query params 'a' and 'b' must be run numbers, e.g. ?a=1&b=2.")

        session_a = get_object_or_404(
            ReadingSession, user=request.user, story_version=version, run_number=run_a
        )
        session_b = get_object_or_404(
            ReadingSession, user=request.user, story_version=version, run_number=run_b
        )

        return Response(RunComparisonSerializer.build(session_a, session_b).data)
