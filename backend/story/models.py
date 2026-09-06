"""
models.py — Core data models for 'ილუზიების გარეშე' / ILUSIEBIS GAReshe
"Stories that reveal the reader."

Layering, matching the product's three-layer principle:
  Layer 1 (Story)          Story, StoryVersion, StoryTheme, StoryNode, Choice
  Layer 2 (Reader)         ReadingSession, ReaderChoice, Bookmark
  Layer 3 (Interpretation) PsychologicalTag, ChoiceTagWeight, Interpretation, Reflection
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# ---------------------------------------------------------------------------
# Layer 1: The Story
# ---------------------------------------------------------------------------


class StoryTheme(models.Model):
    """
    A story-level literary/psychological theme used for discovery and
    browsing (e.g. "grief", "self-deception", "identity"). Distinct from
    PsychologicalTag, which scores individual reader choices rather than
    describing a story as a whole.
    """

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Story(models.Model):
    """
    A library entry — the stable identity of a story across all its
    versions. Everything reader-facing (discovery, bookmarks, reading
    sessions) points at a Story; everything content-facing (nodes,
    choices) belongs to a specific StoryVersion of it.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=255, unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_image_url = models.URLField(blank=True)
    estimated_minutes = models.PositiveIntegerField(
        default=15, help_text="Approximate reading time shown to readers, e.g. 10-25."
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    themes = models.ManyToManyField(StoryTheme, related_name="stories", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["status"])]
        verbose_name_plural = "stories"

    def __str__(self):
        return self.title

    @property
    def published_version(self):
        return self.versions.filter(is_published=True).order_by("-version_number").first()


class StoryVersion(models.Model):
    """
    An immutable, editorial snapshot of a story's content. Authoring
    happens on an unpublished StoryVersion; once is_published=True, its
    StoryNodes and Choices must not be structurally edited — instead,
    create a new StoryVersion so that existing ReadingSessions built on
    an older version remain valid and reproducible.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, related_name="versions", on_delete=models.CASCADE)
    version_number = models.PositiveIntegerField()
    root_node = models.ForeignKey(
        "StoryNode",
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The node a fresh ReadingSession begins at. Set once authoring is complete.",
    )

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["story", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["story", "version_number"], name="unique_version_per_story"
            ),
        ]

    def __str__(self):
        return f"{self.story.title} v{self.version_number}"

    def publish(self):
        """
        Marks this version as the live one. Does not unpublish sibling
        versions automatically — Story.published_version always resolves
        to the highest version_number that is_published, so publishing a
        new version naturally supersedes the old one for new sessions
        while old sessions keep pointing at their original StoryVersion.
        """
        if self.root_node_id is None:
            raise ValidationError("Cannot publish a StoryVersion with no root_node set.")
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=["is_published", "published_at"])

    def validate_graph(self):
        """
        Lightweight structural validation an authoring dashboard can call
        before allowing publish: flags unreachable nodes and dead ends
        that aren't intentional endings. Returns a list of human-readable
        problems; an empty list means the graph is publishable.
        """
        problems = []
        nodes = list(self.nodes.all())
        node_ids = {n.id for n in nodes}

        if self.root_node_id is None:
            problems.append("No root_node set.")
            return problems

        reachable = {self.root_node_id}
        frontier = [self.root_node_id]
        while frontier:
            current = frontier.pop()
            for choice in Choice.objects.filter(source_node_id=current):
                if choice.target_node_id not in reachable:
                    reachable.add(choice.target_node_id)
                    frontier.append(choice.target_node_id)

        unreachable = node_ids - reachable
        for node_id in unreachable:
            problems.append(f"Node {node_id} is unreachable from the root node.")

        for node in nodes:
            has_outgoing = Choice.objects.filter(source_node=node).exists()
            if not has_outgoing and not node.is_ending:
                problems.append(
                    f"Node '{node.slug}' is a dead end but is not marked as an ending."
                )

        return problems


# ---------------------------------------------------------------------------
# Layer 3 (defined early since Choice depends on it): Interpretation tags
# ---------------------------------------------------------------------------


class PsychologicalTag(models.Model):
    """
    A reading-behavior signal (e.g. rejection_assumption, projection,
    threat_oriented_inference) that a Choice can nudge. Deliberately
    framed as an interpretive lens, not a diagnosis — see Interpretation
    below for how this is surfaced to the reader.
    """

    class Category(models.TextChoices):
        DEFENSE_MECHANISM = "defense_mechanism", "Defense Mechanism"
        ARCHETYPE = "archetype", "Jungian Archetype"
        COGNITIVE_BIAS = "cognitive_bias", "Cognitive Bias"
        ATTRIBUTION = "attribution", "Attribution Style"
        EMOTIONAL_TRAIT = "emotional_trait", "Emotional Trait"
        OTHER = "other", "Other"

    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    category = models.CharField(
        max_length=32, choices=Category.choices, default=Category.OTHER
    )
    reader_facing_description = models.TextField(
        blank=True,
        help_text="Non-clinical phrasing shown to the reader, e.g. 'You tended to read ambiguous silence as rejection.'",
    )

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


# ---------------------------------------------------------------------------
# Layer 1 continued: nodes and choices, now scoped to a StoryVersion
# ---------------------------------------------------------------------------


class StoryNode(models.Model):
    """
    A single narrative unit within one StoryVersion: a scene, paragraph
    block, chapter opener, interactive interpretation moment, or ending.
    """

    class NodeType(models.TextChoices):
        STANDARD = "standard", "Standard narrative"
        CHOICE_POINT = "choice_point", "Choice point"
        REFLECTION = "reflection", "Psychological reflection"
        ENDING = "ending", "Ending"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story_version = models.ForeignKey(
        StoryVersion, related_name="nodes", on_delete=models.CASCADE
    )
    chapter_title = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        help_text="Identifier used by clients and authoring tools; unique within its StoryVersion.",
    )
    text_content = models.TextField()
    node_type = models.CharField(
        max_length=20, choices=NodeType.choices, default=NodeType.STANDARD
    )

    is_ending = models.BooleanField(default=False)
    ending_label = models.CharField(max_length=255, blank=True)

    order_index = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["story_version", "node_type"]),
            models.Index(fields=["is_ending"]),
        ]
        ordering = ["story_version", "chapter_title", "order_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["story_version", "slug"], name="unique_slug_per_story_version"
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
    A branching edge in the story graph. source_node and target_node
    must belong to the same StoryVersion — enforced in clean() since
    Django can't express a cross-field FK constraint declaratively.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_node = models.ForeignKey(
        StoryNode, related_name="outgoing_choices", on_delete=models.CASCADE
    )
    target_node = models.ForeignKey(
        StoryNode, related_name="incoming_choices", on_delete=models.CASCADE
    )

    display_text = models.CharField(max_length=500)
    question_text = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional interpretive prompt shown above the options, e.g. 'What do you think she is avoiding?'",
    )
    order_index = models.PositiveIntegerField(default=0)

    psychological_tags = models.ManyToManyField(
        PsychologicalTag, related_name="choices", blank=True, through="ChoiceTagWeight"
    )

    requires_flag = models.CharField(max_length=100, blank=True)

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

    def clean(self):
        if (
            self.source_node_id
            and self.target_node_id
            and self.source_node.story_version_id != self.target_node.story_version_id
        ):
            raise ValidationError(
                "source_node and target_node must belong to the same StoryVersion."
            )


class ChoiceTagWeight(models.Model):
    """Signed weight of a Choice's contribution to a PsychologicalTag score."""

    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    tag = models.ForeignKey(PsychologicalTag, on_delete=models.CASCADE)
    weight = models.SmallIntegerField(default=1)

    class Meta:
        unique_together = ("choice", "tag")

    def __str__(self):
        return f"{self.choice_id} · {self.tag.slug}: {self.weight:+d}"


# ---------------------------------------------------------------------------
# Layer 2: The Reader — replay-capable sessions
# ---------------------------------------------------------------------------


class ReadingSession(models.Model):
    """
    One reading run through a StoryVersion. Unlike the old ReaderProgress,
    a user may have several ReadingSessions for the same StoryVersion —
    run_number distinguishes them and is what makes Replay + Run
    Comparison possible.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reading_sessions", on_delete=models.CASCADE
    )
    story_version = models.ForeignKey(
        StoryVersion, related_name="reading_sessions", on_delete=models.PROTECT
    )
    run_number = models.PositiveIntegerField(
        default=1, help_text="1 for the first read, 2+ for each replay of the same StoryVersion."
    )

    current_node = models.ForeignKey(
        StoryNode, related_name="readers_here", on_delete=models.SET_NULL, null=True
    )

    psychological_profile = models.JSONField(
        default=dict,
        blank=True,
        help_text="Cached tag-slug -> score tally for this run, e.g. {'rejection_assumption': 4}.",
    )
    flags = models.JSONField(default=list, blank=True)

    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "story_version", "is_completed"]),
            models.Index(fields=["last_active_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "story_version", "run_number"],
                name="unique_run_per_user_per_story_version",
            ),
        ]
        ordering = ["user", "story_version", "run_number"]

    def __str__(self):
        return f"{self.user} · {self.story_version} · run {self.run_number}"

    def apply_choice(self, choice):
        """
        Advances the reader, records evidence-linked interpretation for
        every tag the choice carries, and updates the cached tally.
        Returns the created ReaderChoice for the caller to serialize.
        """
        reader_choice = ReaderChoice.objects.create(
            reading_session=self, choice=choice, node_at_time=choice.source_node
        )

        for tag_weight in choice.choicetagweight_set.select_related("tag"):
            key = tag_weight.tag.slug
            self.psychological_profile[key] = (
                self.psychological_profile.get(key, 0) + tag_weight.weight
            )
            Interpretation.objects.create(
                reading_session=self,
                reader_choice=reader_choice,
                tag=tag_weight.tag,
                weight=tag_weight.weight,
            )

        self.current_node = choice.target_node
        if choice.target_node.is_ending:
            self.is_completed = True
            self.completed_at = timezone.now()
        self.save()

        return reader_choice


class ReaderChoice(models.Model):
    """Append-only history of every choice made within a ReadingSession."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reading_session = models.ForeignKey(
        ReadingSession, related_name="choice_history", on_delete=models.CASCADE
    )
    choice = models.ForeignKey(Choice, related_name="log_entries", on_delete=models.PROTECT)
    node_at_time = models.ForeignKey(StoryNode, related_name="+", on_delete=models.PROTECT)

    made_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reading_session", "made_at"]
        indexes = [models.Index(fields=["reading_session", "made_at"])]

    def __str__(self):
        return f"{self.reading_session} chose {self.choice_id} at {self.made_at}"


class Bookmark(models.Model):
    """A reader-saved position in a story, independent of an active session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="bookmarks", on_delete=models.CASCADE
    )
    story = models.ForeignKey(Story, related_name="bookmarks", on_delete=models.CASCADE)
    node = models.ForeignKey(StoryNode, related_name="+", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "story"], name="one_bookmark_per_user_per_story"),
        ]

    def __str__(self):
        return f"{self.user} bookmarked {self.story}"


# ---------------------------------------------------------------------------
# Layer 3 continued: transparent, evidence-linked interpretation
# ---------------------------------------------------------------------------


class Interpretation(models.Model):
    """
    A single piece of evidence behind a reader's psychological_profile:
    "this ReaderChoice contributed +2 to rejection_assumption." Reflection
    (below) aggregates these into the end-of-story summary, and the
    reader can always drill from a claim back to the exact choices that
    produced it — never a black-box conclusion.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reading_session = models.ForeignKey(
        ReadingSession, related_name="interpretations", on_delete=models.CASCADE
    )
    reader_choice = models.ForeignKey(
        ReaderChoice, related_name="interpretations", on_delete=models.CASCADE
    )
    tag = models.ForeignKey(PsychologicalTag, related_name="interpretations", on_delete=models.CASCADE)
    weight = models.SmallIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["reading_session", "created_at"]
        indexes = [models.Index(fields=["reading_session", "tag"])]

    def __str__(self):
        return f"{self.reading_session} · {self.tag.slug} {self.weight:+d}"


class Reflection(models.Model):
    """
    The generated end-of-story reflection for one completed ReadingSession.
    Cached once generated (by the AI analysis layer or a deterministic
    summarizer) so it doesn't need to be recomputed on every view, and so
    a Run Comparison can diff two Reflections directly.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reading_session = models.OneToOneField(
        ReadingSession, related_name="reflection", on_delete=models.CASCADE
    )
    summary_text = models.TextField(
        help_text="Reader-facing summary, e.g. 'You repeatedly interpreted silence as rejection.'"
    )
    strongest_tag = models.ForeignKey(
        PsychologicalTag,
        related_name="+",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The tag with the highest accumulated weight this run, if any.",
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reflection for {self.reading_session}"
