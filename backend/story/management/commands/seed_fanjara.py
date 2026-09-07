"""
seed_fanjara.py — Creates, wires up, validates, and publishes the
"ფანჯარა" story end to end. Idempotent: safe to run more than once,
since it uses get_or_create/update_or_create throughout rather than
plain create().

Usage:
    python manage.py seed_fanjara
"""

from django.core.management.base import BaseCommand, CommandError

from story.models import (
    Choice,
    ChoiceTagWeight,
    PsychologicalTag,
    Story,
    StoryNode,
    StoryVersion,
)


class Command(BaseCommand):
    help = "Seeds, validates, and publishes the ფანჯარა story."

    def handle(self, *args, **options):
        story, story_created = Story.objects.update_or_create(
            slug="fanjara",
            defaults={
                "title": "ფანჯარა",
                "description": "მოკლე ისტორია იმაზე, თუ როგორ ავსებთ სიჩუმეს ჩვენივე ვარაუდებით.",
                "estimated_minutes": 5,
                # Deliberately not set to published yet — that happens at the
                # end, only after the graph validates cleanly.
            },
        )
        self.log_created_or_found("Story", story, story_created)

        version, version_created = StoryVersion.objects.get_or_create(
            story=story, version_number=1
        )
        self.log_created_or_found("StoryVersion", version, version_created)

        tag_rejection, _ = PsychologicalTag.objects.update_or_create(
            slug="uaryofis_varaudi",
            defaults={
                "name": "უარყოფის ვარაუდი",
                "category": PsychologicalTag.Category.ATTRIBUTION,
                "reader_facing_description": (
                    "თქვენ არაერთხელ აღიქვით სიჩუმე უარყოფად, სანამ ისტორია "
                    "რამეს დაადასტურებდა ან უარყოფდა."
                ),
            },
        )
        tag_openness, _ = PsychologicalTag.objects.update_or_create(
            slug="ghia_ganmartebeloba",
            defaults={
                "name": "ღიაობა განმარტებისადმი",
                "category": PsychologicalTag.Category.COGNITIVE_BIAS,
                "reader_facing_description": (
                    "თქვენ დარჩით ღია რამდენიმე ახსნისთვის მაშინაც კი, როცა "
                    "სიტუაცია გაურკვეველი იყო."
                ),
            },
        )
        self.stdout.write(self.style.SUCCESS("PsychologicalTags ready."))

        opening, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="gaxsna",
            defaults={
                "chapter_title": "თავი 1",
                "text_content": (
                    "მან დაინახა ის ფანჯარასთან. ის არ შეხედავს მას. "
                    "სიჩუმე გაგრძელდა იმაზე დიდხანს, ვიდრე საჭირო იყო."
                ),
                "node_type": StoryNode.NodeType.CHOICE_POINT,
                "is_ending": False,
            },
        )
        rejection_end, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="uaryofa",
            defaults={
                "chapter_title": "თავი 1",
                "text_content": (
                    "თქვენ ივარაუდეთ ყველაზე უარესი და მოშორდით. მოგვიანებით "
                    "გაიგებთ, რომ ის უბრალოდ დაფიქრებული იყო წერილზე, "
                    "რომელიც დილით მიიღო."
                ),
                "node_type": StoryNode.NodeType.ENDING,
                "is_ending": True,
                "ending_label": "დაშვებული უარყოფა",
            },
        )
        openness_end, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="siciyvle",
            defaults={
                "chapter_title": "თავი 1",
                "text_content": (
                    "თქვენ დარჩით და ჰკითხეთ. აღმოჩნდა, რომ ის საერთოდ არ "
                    "გერიდებოდათ — უბრალოდ დაფიქრებული იყო წერილზე, "
                    "რომელიც დილით მიიღო."
                ),
                "node_type": StoryNode.NodeType.ENDING,
                "is_ending": True,
                "ending_label": "ღიაობა",
            },
        )
        self.stdout.write(self.style.SUCCESS("StoryNodes ready: gaxsna, uaryofa, siciyvle."))

        choice_reject, _ = Choice.objects.update_or_create(
            source_node=opening,
            target_node=rejection_end,
            defaults={"display_text": "ის თავს არიდებს მე", "order_index": 0},
        )
        ChoiceTagWeight.objects.update_or_create(
            choice=choice_reject, tag=tag_rejection, defaults={"weight": 3}
        )

        choice_open, _ = Choice.objects.update_or_create(
            source_node=opening,
            target_node=openness_end,
            defaults={"display_text": "ის რაღაცას იხსენებს", "order_index": 1},
        )
        ChoiceTagWeight.objects.update_or_create(
            choice=choice_open, tag=tag_openness, defaults={"weight": 2}
        )
        self.stdout.write(self.style.SUCCESS("Choices + tag weights ready."))

        version.root_node = opening
        version.save(update_fields=["root_node"])

        problems = version.validate_graph()
        if problems:
            raise CommandError(
                "Graph validation failed, refusing to publish:\n" + "\n".join(problems)
            )
        self.stdout.write(self.style.SUCCESS("Graph validation passed."))

        if not version.is_published:
            version.publish()
        self.stdout.write(self.style.SUCCESS(f"{version} published."))

        if story.status != Story.Status.PUBLISHED:
            story.status = Story.Status.PUBLISHED
            story.save(update_fields=["status"])
        self.stdout.write(self.style.SUCCESS(f"'{story.title}' is now published."))

        self.stdout.write(self.style.SUCCESS("\nDone. Refresh /library in the reader."))

    def log_created_or_found(self, label, obj, created):
        verb = "Created" if created else "Found existing"
        self.stdout.write(f"{verb} {label}: {obj}")
