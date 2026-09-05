"""
models.py — Core data models for 'ილუზიების გარეშე'
Interactive storytelling + analytical psychology tracking engine.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class PsychologicalTag(models.Model):
    """
    A reusable psychological construct (e.g. projection, rationalization,
    denial, sublimation) that can be attached to Choices to build up
    a reader's psychological profile over time.
    """

    class Category(models.TextChoices):
        DEFENSE_MECHANISM = "defense_mechanism", "Defense Mechanism"
        ARCHETYPE = "archetype", "Jungian Archetype"
        COGNITIVE_BIAS = "cognitive_bias", "Cognitive Bias"
        EMOTIONAL_TRAIT = "emotional_trait", "Emotional Trait"
        OTHER = "other", "Other"

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    category = models.CharField(
        max_length=32, choices=Category.choices, default=Category.OTHER
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class StoryNode(models.Model):
    """
    A single narrative unit: a scene, paragraph block, chapter opener,
    or a psychological reflection prompt. Nodes are linked into a
    branching graph via Choice objects.
    """

    class NodeType(models.TextChoices):
        STANDARD = "standard", "Standard narrative"
        CHOICE_POINT = "choice_point", "Choice point"
        REFLECTION = "reflection", "Psychological reflection"
        ENDING = "ending", "Ending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chapter_title = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        unique=True,
        help_text="Stable identifier used by the Flutter client and content tools.",
    )
    text_content = models.TextField()
    node_type = models.CharField(
        max_length=20, choices=NodeType.choices, default=NodeType.STANDARD
    )

    is_ending = models.BooleanField(
        default=False,
        help_text="True if reaching this node terminates the current story path.",
    )
    ending_label = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. 'The Shadow Accepted', 'Denial Loop' — only used when is_ending=True.",
    )
    is_start = models.BooleanField(
        default=False,
        help_text="Marks the node a fresh ReaderProgress should begin at. Exactly one per story.",
    )

    order_index = models.PositiveIntegerField(
        default=0,
        help_text="Authoring-time ordering within a chapter; not used for graph traversal.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["node_type"]),
            models.Index(fields=["is_ending"]),
            models.Index(fields=["chapter_title", "order_index"]),
        ]
        ordering = ["chapter_title", "order_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_start"],
                condition=models.Q(is_start=True),
                name="only_one_start_node",
            ),
        ]

    def __str__(self):
        return f"[{self.node_type}] {self.chapter_title} — {self.slug}"

    def clean(self):
        if self.is_ending and self.node_type != self.NodeType.ENDING:
            raise ValidationError(
                "is_ending=True requires node_type=ENDING for consistency."
            )


class Choice(models.Model):
    """
    A branching edge in the story graph: an action the reader can take
    from `source_node` that leads to `target_node`. Choices carry
    psychological metadata (via ChoiceTagWeight) used to build the
    reader's profile.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_node = models.ForeignKey(
        StoryNode, related_name="outgoing_choices", on_delete=models.CASCADE
    )
    target_node = models.ForeignKey(
        StoryNode, related_name="incoming_choices", on_delete=models.CASCADE
    )

    display_text = models.CharField(
        max_length=500, help_text="The text shown to the reader for this option."
    )
    order_index = models.PositiveIntegerField(
        default=0, help_text="Display order among sibling choices from the same source_node."
    )

    psychological_tags = models.ManyToManyField(
        PsychologicalTag,
        related_name="choices",
        blank=True,
        through="ChoiceTagWeight",
    )

    requires_flag = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional gating condition — a flag that must be present in ReaderProgress.flags for this choice to appear.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["source_node", "order_index"]),
            models.Index(fields=["target_node"]),
        ]
        ordering = ["source_node", "order_index"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source_node=models.F("target_node")),
                name="choice_no_self_loop",
            ),
        ]

    def __str__(self):
        return f"{self.source_node.slug} -> {self.target_node.slug}: {self.display_text[:40]}"


class ChoiceTagWeight(models.Model):
    """
    Through-model linking a Choice to a PsychologicalTag with a signed
    weight, so a single choice can nudge multiple psychological
    dimensions by different amounts (e.g. +2 rationalization, +1 avoidance,
    -1 confrontation).
    """

    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    tag = models.ForeignKey(PsychologicalTag, on_delete=models.CASCADE)
    weight = models.SmallIntegerField(
        default=1,
        help_text="Signed contribution to the reader's score for this tag when this choice is picked.",
    )

    class Meta:
        unique_together = ("choice", "tag")

    def __str__(self):
        return f"{self.choice_id} · {self.tag.slug}: {self.weight:+d}"


class ReaderProgress(models.Model):
    """
    One row per active reader — tracks where they currently are in the
    graph, their accumulated psychological profile, and any narrative
    flags they've picked up. The detailed history of individual choices
    lives in ChoiceLog for full auditability and replay.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reading_progress", on_delete=models.CASCADE
    )

    current_node = models.ForeignKey(
        StoryNode, related_name="readers_here", on_delete=models.SET_NULL, null=True
    )

    psychological_profile = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Denormalized cache of accumulated tag scores, e.g. "
            "{'rationalization': 4, 'projection': -1}. Derived from "
            "ChoiceLog + ChoiceTagWeight, kept here for fast reads."
        ),
    )
    flags = models.JSONField(
        default=list,
        blank=True,
        help_text="Narrative flags collected so far, used to gate Choice.requires_flag.",
    )

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_completed"]),
            models.Index(fields=["last_active_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user"], name="one_active_progress_per_user"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.current_node_id or 'unstarted'}"

    def apply_choice(self, choice: "Choice") -> None:
        """
        Advances the reader to choice.target_node, logs the choice for
        audit/replay, and updates the cached psychological_profile.
        Caller is responsible for validating that `choice` is actually
        a legal option from self.current_node (see views.SubmitChoiceView).
        """
        for tag_weight in choice.choicetagweight_set.select_related("tag"):
            key = tag_weight.tag.slug
            self.psychological_profile[key] = (
                self.psychological_profile.get(key, 0) + tag_weight.weight
            )

        self.current_node = choice.target_node
        if choice.target_node.is_ending:
            self.is_completed = True
            self.completed_at = timezone.now()
        self.save()

        ChoiceLog.objects.create(
            reader_progress=self, choice=choice, node_at_time=choice.source_node
        )


class ChoiceLog(models.Model):
    """
    Append-only history of every choice a reader has made — the full
    path taken through the story graph. Enables replay, analytics, and
    reconstructing exactly why a psychological_profile ended up as it did.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader_progress = models.ForeignKey(
        ReaderProgress, related_name="choice_history", on_delete=models.CASCADE
    )
    choice = models.ForeignKey(Choice, related_name="log_entries", on_delete=models.PROTECT)
    node_at_time = models.ForeignKey(
        StoryNode,
        related_name="+",
        on_delete=models.PROTECT,
        help_text="Snapshot of the source node at choice-time, in case the graph is edited later.",
    )

    made_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reader_progress", "made_at"]
        indexes = [
            models.Index(fields=["reader_progress", "made_at"]),
        ]

    def __str__(self):
        return f"{self.reader_progress.user} chose {self.choice_id} at {self.made_at}"
