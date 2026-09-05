"""
views.py — Reader-facing story API.

Three endpoints power the Flutter client's core loop:
  GET  /api/story/current/   -> current node + available choices
  POST /api/story/choice/    -> submit a choice, advance the graph
  GET  /api/story/profile/   -> the reader's psychological profile cache
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Choice, ReaderProgress, StoryNode
from .serializers import (
    PsychologicalProfileSerializer,
    StoryNodeSerializer,
    SubmitChoiceSerializer,
)


def get_or_create_progress(user) -> ReaderProgress:
    """
    Fetches the reader's single active ReaderProgress row, creating one
    anchored at the story's designated start node if this is their
    first visit. Relies on StoryNode.is_start being unique (enforced by
    a partial unique constraint at the DB level).
    """
    progress, created = ReaderProgress.objects.get_or_create(
        user=user,
        defaults={"current_node": get_object_or_404(StoryNode, is_start=True)},
    )
    return progress


class CurrentNodeView(APIView):
    """Returns the node the reader is currently on, with live choices."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        progress = get_or_create_progress(request.user)

        if progress.current_node is None:
            return Response(
                {"detail": "No current node set for this reader."},
                status=status.HTTP_409_CONFLICT,
            )

        node = (
            StoryNode.objects.prefetch_related("outgoing_choices")
            .get(pk=progress.current_node_id)
        )
        serializer = StoryNodeSerializer(node, context={"reader_progress": progress})
        return Response(serializer.data)


class SubmitChoiceView(APIView):
    """
    Validates and applies a reader's choice, atomically advancing
    ReaderProgress and returning the resulting node + updated profile.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        input_serializer = SubmitChoiceSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        choice_id = input_serializer.validated_data["choice_id"]

        # Lock the reader's progress row for the duration of the
        # transaction to prevent double-submission races (e.g. a
        # retried request from a flaky mobile connection).
        progress = (
            ReaderProgress.objects.select_for_update()
            .get(user=request.user)
        )

        if progress.is_completed:
            raise ValidationError("This reader has already reached an ending.")

        choice = get_object_or_404(
            Choice.objects.select_related("source_node", "target_node"),
            pk=choice_id,
        )

        if choice.source_node_id != progress.current_node_id:
            raise ValidationError(
                "That choice is not available from the reader's current node."
            )

        if choice.requires_flag and choice.requires_flag not in progress.flags:
            raise ValidationError("This choice is gated behind a flag the reader hasn't collected.")

        progress.apply_choice(choice)

        node_serializer = StoryNodeSerializer(
            progress.current_node, context={"reader_progress": progress}
        )
        return Response(
            {
                "node": node_serializer.data,
                "profile": PsychologicalProfileSerializer.from_progress(progress).data,
            }
        )


class ProfileView(APIView):
    """Returns just the reader's accumulated psychological profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        progress = get_or_create_progress(request.user)
        serializer = PsychologicalProfileSerializer.from_progress(progress)
        return Response(serializer.data)
