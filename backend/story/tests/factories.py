"""
factories.py — Builds a small, deterministic story graph for tests:

    opening (choice_point)
      -> "She is avoiding him"   -> reads-rejection (ending), +3 rejection_assumption
      -> "Something she remembers" -> stays-curious (ending), no tag weight

Kept as plain functions rather than factory_boy to avoid an extra
dependency for a graph this small.
"""

from story.models import Choice, ChoiceTagWeight, PsychologicalTag, Story, StoryNode, StoryVersion


def build_published_story(slug="the-window", title="The Window"):
    story = Story.objects.create(slug=slug, title=title, status=Story.Status.PUBLISHED)
    version = StoryVersion.objects.create(story=story, version_number=1)

    start = StoryNode.objects.create(
        story_version=version,
        chapter_title="Ch1",
        slug="opening",
        text_content="He saw her standing beside the window. She did not look at him.",
        node_type=StoryNode.NodeType.CHOICE_POINT,
    )
    node_reject = StoryNode.objects.create(
        story_version=version,
        chapter_title="Ch1",
        slug="reads-rejection",
        text_content="You assumed the worst.",
        node_type=StoryNode.NodeType.ENDING,
        is_ending=True,
        ending_label="Assumed Rejection",
    )
    node_curious = StoryNode.objects.create(
        story_version=version,
        chapter_title="Ch1",
        slug="stays-curious",
        text_content="You stayed curious.",
        node_type=StoryNode.NodeType.ENDING,
        is_ending=True,
        ending_label="Stayed Open",
    )

    version.root_node = start
    version.save()

    tag, _ = PsychologicalTag.objects.get_or_create(
        slug="rejection_assumption",
        defaults={
            "name": "Rejection Assumption",
            "category": PsychologicalTag.Category.ATTRIBUTION,
            "reader_facing_description": "You repeatedly interpreted silence as rejection.",
        },
    )

    choice_reject = Choice.objects.create(
        source_node=start,
        target_node=node_reject,
        display_text="She is avoiding him",
        question_text="What do you think she is avoiding?",
        order_index=0,
    )
    choice_curious = Choice.objects.create(
        source_node=start,
        target_node=node_curious,
        display_text="Something she remembers",
        order_index=1,
    )
    ChoiceTagWeight.objects.create(choice=choice_reject, tag=tag, weight=3)

    version.publish()

    return {
        "story": story,
        "version": version,
        "start": start,
        "node_reject": node_reject,
        "node_curious": node_curious,
        "choice_reject": choice_reject,
        "choice_curious": choice_curious,
        "tag": tag,
    }
