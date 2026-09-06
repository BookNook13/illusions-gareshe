"""
serializers.py — Reader-facing (Flutter/Next.js) serialization.

These expose only what a *reader* should see: never target_node ids for
unvisited choices' internals, never raw ChoiceTagWeight values — only
the reader-facing description once an Interpretation has actually fired.
"""

from rest_framework import serializers

from .models import (
    Bookmark,
    Choice,
    Interpretation,
    ReaderChoice,
    ReadingSession,
    Reflection,
    Story,
    StoryNode,
    StoryTheme,
    StoryVersion,
)


class StoryThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryTheme
        fields = ["slug", "name", "description"]


class StoryListSerializer(serializers.ModelSerializer):
    """Discovery / library view — one row per Story, not per version."""

    themes = StoryThemeSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = [
            "id",
            "slug",
            "title",
            "description",
            "cover_image_url",
            "estimated_minutes",
            "themes",
        ]
        read_only_fields = fields


class ChoiceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "display_text", "order_index"]
        read_only_fields = fields


class StoryNodeSerializer(serializers.ModelSerializer):
    """The node currently being read, with the question text (if any) and live choices."""

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
        session: ReadingSession = self.context["session"]
        available = [
            choice
            for choice in node.outgoing_choices.all().order_by("order_index")
            if not choice.requires_flag or choice.requires_flag in session.flags
        ]
        return ChoiceOptionSerializer(available, many=True).data


class InterpretationSerializer(serializers.ModelSerializer):
    """One piece of evidence: this choice contributed this much to this tag."""

    tag_slug = serializers.CharField(source="tag.slug", read_only=True)
    tag_name = serializers.CharField(source="tag.name", read_only=True)
    reader_facing_description = serializers.CharField(
        source="tag.reader_facing_description", read_only=True
    )
    choice_text = serializers.CharField(source="reader_choice.choice.display_text", read_only=True)

    class Meta:
        model = Interpretation
        fields = [
            "id",
            "tag_slug",
            "tag_name",
            "reader_facing_description",
            "weight",
            "choice_text",
            "created_at",
        ]
        read_only_fields = fields


class PsychologicalProfileSerializer(serializers.Serializer):
    """Read-only view of a session's accumulated profile, with drill-down evidence."""

    profile = serializers.DictField(child=serializers.IntegerField())
    flags = serializers.ListField(child=serializers.CharField())
    is_completed = serializers.BooleanField()
    run_number = serializers.IntegerField()

    @classmethod
    def from_session(cls, session: ReadingSession) -> "PsychologicalProfileSerializer":
        return cls(
            {
                "profile": session.psychological_profile,
                "flags": session.flags,
                "is_completed": session.is_completed,
                "run_number": session.run_number,
            }
        )


class ReflectionSerializer(serializers.ModelSerializer):
    interpretations = InterpretationSerializer(
        source="reading_session.interpretations", many=True, read_only=True
    )
    strongest_tag_slug = serializers.CharField(source="strongest_tag.slug", read_only=True)

    class Meta:
        model = Reflection
        fields = ["id", "summary_text", "strongest_tag_slug", "interpretations", "generated_at"]
        read_only_fields = fields


class RunComparisonSerializer(serializers.Serializer):
    """Side-by-side diff of two ReadingSessions (runs) for the same StoryVersion."""

    run_a = serializers.IntegerField()
    run_b = serializers.IntegerField()
    profile_a = serializers.DictField(child=serializers.IntegerField())
    profile_b = serializers.DictField(child=serializers.IntegerField())
    diverging_choices = serializers.ListField()

    @classmethod
    def build(cls, session_a: ReadingSession, session_b: ReadingSession):
        history_a = list(session_a.choice_history.select_related("choice", "node_at_time"))
        history_b = list(session_b.choice_history.select_related("choice", "node_at_time"))

        diverging = []
        for entry_a, entry_b in zip(history_a, history_b):
            if entry_a.choice_id != entry_b.choice_id:
                diverging.append(
                    {
                        "node_slug": entry_a.node_at_time.slug,
                        "run_a_choice": entry_a.choice.display_text,
                        "run_b_choice": entry_b.choice.display_text,
                    }
                )

        return cls(
            {
                "run_a": session_a.run_number,
                "run_b": session_b.run_number,
                "profile_a": session_a.psychological_profile,
                "profile_b": session_b.psychological_profile,
                "diverging_choices": diverging,
            }
        )


class SubmitChoiceSerializer(serializers.Serializer):
    choice_id = serializers.UUIDField()


class BookmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ["id", "story", "node", "created_at"]
        read_only_fields = ["id", "created_at"]
