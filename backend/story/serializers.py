"""
serializers.py — Reader-facing (Flutter client) serialization.

Design principle: these serializers expose only what a *reader* should
see. They never leak target_node ids, psychological_tags/weights, or
other authoring metadata that would spoil the narrative or the
psychological mechanic being studied.
"""

from rest_framework import serializers

from .models import Choice, ReaderProgress, StoryNode


class ChoiceOptionSerializer(serializers.ModelSerializer):
    """A single option presented to the reader at a choice point."""

    class Meta:
        model = Choice
        fields = ["id", "display_text", "order_index"]
        read_only_fields = fields


class StoryNodeSerializer(serializers.ModelSerializer):
    """
    The node currently being read, plus the choices available *from*
    it, already filtered against the reader's collected flags.
    """

    choices = serializers.SerializerMethodField()

    class Meta:
        model = StoryNode
        fields = [
            "id",
            "slug",
            "chapter_title",
            "text_content",
            "node_type",
            "is_ending",
            "ending_label",
            "choices",
        ]
        read_only_fields = fields

    def get_choices(self, node: StoryNode):
        reader_progress: ReaderProgress = self.context["reader_progress"]
        available = [
            choice
            for choice in node.outgoing_choices.all().order_by("order_index")
            if not choice.requires_flag or choice.requires_flag in reader_progress.flags
        ]
        return ChoiceOptionSerializer(available, many=True).data


class PsychologicalProfileSerializer(serializers.Serializer):
    """
    Read-only view of the reader's accumulated profile. Kept as a plain
    Serializer (not ModelSerializer) since the shape is a free-form
    tag-slug -> score mapping, not a fixed set of model fields.
    """

    profile = serializers.DictField(child=serializers.IntegerField())
    flags = serializers.ListField(child=serializers.CharField())
    is_completed = serializers.BooleanField()

    @classmethod
    def from_progress(cls, progress: ReaderProgress) -> "PsychologicalProfileSerializer":
        return cls(
            {
                "profile": progress.psychological_profile,
                "flags": progress.flags,
                "is_completed": progress.is_completed,
            }
        )


class SubmitChoiceSerializer(serializers.Serializer):
    """Input payload for POST /api/story/choice/."""

    choice_id = serializers.UUIDField()
