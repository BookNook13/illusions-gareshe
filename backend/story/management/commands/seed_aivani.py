"""
seed_aivani.py — Creates, validates, and publishes "აივანი" (The Balcony),
a story drafted by Gemini from a prompt grounded in the project's
Illusionless philosophy, then verified and wired into the schema here.

Deliberately reuses the same three PsychologicalTags as წერილი
(realobis_uaryofa / gaciveba / sitskhade) rather than creating new ones —
denial, hardness, and clarity are the same underlying pattern across
situations, and sharing tags is what lets a reader's tendency toward one
of them accumulate across stories instead of resetting each time.

Idempotent: safe to run more than once.

Usage:
    python manage.py seed_aivani
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
    help = "Seeds, validates, and publishes აივანი (The Balcony)."

    def handle(self, *args, **options):
        story, created = Story.objects.update_or_create(
            slug="aivani",
            defaults={
                "title": "აივანი",
                "description": (
                    "ღამის აივანზე გაგონილი ერთი წინადადება ანგრევს იმას, "
                    "რასაც სიმშვიდე ერქვა."
                ),
                "estimated_minutes": 7,
            },
        )
        self.log("Story", story, created)

        version, created = StoryVersion.objects.get_or_create(
            story=story, version_number=1
        )
        self.log("StoryVersion", version, created)

        # Reused from წერილი — get_or_create only, so we don't overwrite
        # whichever wording is already live if seed_tserili ran first.
        tag_denial, _ = PsychologicalTag.objects.get_or_create(
            slug="realobis_uaryofa",
            defaults={
                "name": "რეალობის უარყოფა",
                "category": PsychologicalTag.Category.DEFENSE_MECHANISM,
                "reader_facing_description": (
                    "შენ მიდრეკილი ხარ, სიჩუმე სიმშვიდედ წაიკითხო, თუნდაც "
                    "ეს სიჩუმე შეუმჩნეველი, მაგრამ გარდაუვალი გაუცხოების "
                    "ფასად გიჯდებოდეს."
                ),
            },
        )
        tag_hardness, _ = PsychologicalTag.objects.get_or_create(
            slug="gaciveba",
            defaults={
                "name": "გაციება",
                "category": PsychologicalTag.Category.DEFENSE_MECHANISM,
                "reader_facing_description": (
                    "შენ მიდრეკილი ხარ, ილუზიის მსხვრევა პირად ღალატად "
                    "წაიკითხო და თავდაცვის მიზნით, სიმკაცრე და სიცივე "
                    "სიძლიერედ აქციო."
                ),
            },
        )
        tag_clarity, _ = PsychologicalTag.objects.get_or_create(
            slug="sitskhade",
            defaults={
                "name": "სიცხადე",
                "category": PsychologicalTag.Category.OTHER,
                "reader_facing_description": (
                    "შენ მიდრეკილი ხარ, ადამიანური სისუსტეები დაინახო "
                    "სრული სიცხადით, ილუზიების გარეშე, მაგრამ არ აძლევ "
                    "მათ უფლებას, წაგართვან სინაზე და თანაგრძნობის უნარი."
                ),
            },
        )
        self.stdout.write(self.style.SUCCESS("PsychologicalTags ready (shared with წერილი)."))

        opening, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="aivani_scena",
            defaults={
                "chapter_title": "სცენა 1: აივანი და სველი ასფალტი",
                "text_content": (
                    "ღამის თბილისს წვიმის შემდგომი, მძიმე სუნი ასდიოდა. ანა "
                    "აივანზე იდგა და ქოთნებში ჩამჯდარ სველ მიწას უყურებდა. "
                    "ქვემოთ, ეზოს სიბნელეში, ზურას სიგარეტის წითელი წერტილი "
                    "ციმციმებდა. ბოლო თვეების სიმშვიდე — მათი პატარა, "
                    "მყუდრო ილუზია, რომ ფინანსურმა კრიზისმა საბოლოოდ "
                    "გადაიარა და ყველაფერი რიგზეა — სხეულში თბილად "
                    "ეღვრებოდა. სანამ ხმა არ შემოესმა.\n\n"
                    "ზურა ტელეფონზე საუბრობდა, ხმადაბლა, მაგრამ ღამის "
                    "სიჩუმეში სიტყვები ზემოთ მკაფიოდ ამოდიოდა: „...არა, "
                    "ბინა უკვე ჩავდე. ანას არაფერი უთხრა. მას ჰგონია, რომ "
                    "ვალები დავფარეთ. ვერ გადაიტანს, მინდა, რომ თავი "
                    "დაცულად იგრძნოს.“\n\n"
                    "ჰაერი გაიყინა. ილუზია, რომ ისინი ერთმანეთს ყველაფერს "
                    "უზიარებდნენ, რომ მათი სიმშვიდე ნამდვილი და "
                    "გამჭვირვალე იყო, წამში დაიმსხვრა. ანამ იგრძნო, როგორ "
                    "შემოეპარა სიცივე კანქვეშ."
                ),
                "node_type": StoryNode.NodeType.CHOICE_POINT,
                "is_ending": False,
            },
        )

        denial_end, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="usaprtkho_sichume",
            defaults={
                "chapter_title": "ფინალი 1",
                "text_content": (
                    "ანამ ნელა დაიხია უკან. აივნის კარი უხმოდ მიხურა, "
                    "ფარდა ჩამოაფარა და საძინებელში შევიდა. ლოგინში შეწვა "
                    "და თვალები დახუჭა. როცა ათი წუთის შემდეგ ზურა ოთახში "
                    "შემოვიდა, მას სიგარეტისა და სველი ქუჩის სუნი "
                    "შემოჰყვა. „გღვიძავს?“ — იკითხა მან ჩურჩულით. ანამ "
                    "შეიშმუშნა, მაგრამ არ უპასუხა. ილუზია შენარჩუნდა — "
                    "ხვალ დილით ისინი ისევ ერთად დალევენ ყავას და "
                    "ილაპარაკებენ გეგმებზე, რომლებიც უკვე ფიქციაა. მაგრამ "
                    "ამიერიდან, ყოველ შეხებაში, ყოველ ღიმილში, უხილავი "
                    "შუშის კედელი იდგება. სიმშვიდე გადარჩა, მაგრამ ნამდვილი "
                    "სიახლოვე ამაღამ, ამ საძინებელში, უხმოდ დასრულდა."
                ),
                "node_type": StoryNode.NodeType.ENDING,
                "is_ending": True,
                "ending_label": "უსაფრთხო სიჩუმე",
            },
        )

        turning_point, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="tvalis_gasworeba",
            defaults={
                "chapter_title": "შუალედური სცენა: თვალის გასწორება",
                "text_content": (
                    "ანა არ განძრეულა. თითები რკინის მოაჯირს მაგრად "
                    "მოუჭირა. ზურამ ტელეფონი გათიშა, ღრმად ამოისუნთქა და "
                    "ზემოთ ამოიხედა. მათი მზერა ერთმანეთს შეხვდა. "
                    "სიბნელეშიც კი, ანამ დაინახა ზურას სახეზე აღბეჭდილი "
                    "პანიკა — ის მიხვდა, რომ ანამ ყველაფერი გაიგო. წლების "
                    "განმავლობაში ნაშენები გამჭვირვალობის მითი დაინგრა. "
                    "ზურა არ იყო ის კლდესავით საყრდენი, როგორადაც თავს "
                    "აჩვენებდა; ის იყო შეშინებული, შეცდომის დამშვები "
                    "ადამიანი, რომელიც საკუთარ შიშს „ზრუნვას“ არქმევდა."
                ),
                "node_type": StoryNode.NodeType.CHOICE_POINT,
                "is_ending": False,
            },
        )

        hardness_end, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="tsivi_javshani",
            defaults={
                "chapter_title": "ფინალი 2",
                "text_content": (
                    "ანამ მზერა არ აარიდა, მაგრამ რაღაც სამუდამოდ ჩაკვდა "
                    "მის შიგნით. როცა ზურა კიბეებზე ამოდიოდა, ანამ უბრალოდ "
                    "გააცნობიერა, რომ ადამიანი, ვისთანაც წლები გაატარა, "
                    "სუსტი და მატყუარა იყო. მან გადაწყვიტა, რომ აღარასდროს "
                    "მისცემდა ვინმეს უფლებას, ასე მწარედ მოეტყუებინა. "
                    "ზურა ოთახში შემოვიდა და თავის მართლება სცადა, მაგრამ "
                    "ანა იდგა ცივი, უგრძნობი და მიუწვდომელი. ეს იყო "
                    "სიძლიერე, რომელმაც ის ტკივილისგან მყისიერად დაიცვა, "
                    "მაგრამ სანაცვლოდ სამყარო დაცარიელდა. მან პირდაპირ "
                    "შეხედა სიმართლეს, მაგრამ ამ სიმართლემ ის სასტიკ "
                    "ადამიანად აქცია."
                ),
                "node_type": StoryNode.NodeType.ENDING,
                "is_ending": True,
                "ending_label": "ცივი ჯავშანი",
            },
        )

        clarity_end, _ = StoryNode.objects.update_or_create(
            story_version=version,
            slug="mdzime_sitskhade",
            defaults={
                "chapter_title": "ფინალი 3",
                "text_content": (
                    "ანას ყელი გაუშრა. მითი იდეალურ, ურღვევ პარტნიორობაზე "
                    "ერთ წამში აორთქლდა. მაგრამ როცა ზურა ოთახში შემოვიდა "
                    "— მხრებში მოხრილი, შეშინებული, დანაშაულის გრძნობით "
                    "სავსე — ანამ მასში ვერ დაინახა მონსტრი. მან დაინახა "
                    "ადამიანი, რომელსაც ეშინოდა რეალობასთან შეჯახების და "
                    "საკუთარი სისუსტის აღიარების. ანას არ უცდია მისი "
                    "გამართლება, არც ტყუილის იგნორირება — იმედგაცრუება "
                    "მწარე და ნამდვილი იყო. „დაჯექი, ახლა ყველაფერი "
                    "უნდა მომიყვე,“ — თქვა მან ხმადაბლა. ეს საუბარი "
                    "იქნებოდა მტკივნეული და შეუბრალებლად რეალური. მან "
                    "აირჩია ეტარა სიმართლის მთელი სიმძიმე ისე, რომ "
                    "პასუხისმგებლობა და ადამიანური სინაზე არ დაეკარგა."
                ),
                "node_type": StoryNode.NodeType.ENDING,
                "is_ending": True,
                "ending_label": "მძიმე სიცხადე",
            },
        )
        self.stdout.write(self.style.SUCCESS("StoryNodes ready."))

        c1, _ = Choice.objects.update_or_create(
            source_node=opening,
            target_node=denial_end,
            defaults={
                "display_text": "უკან, ოთახში უხმოდ შებრუნება და შუშის კარის მიხურვა",
                "order_index": 0,
            },
        )
        ChoiceTagWeight.objects.update_or_create(
            choice=c1, tag=tag_denial, defaults={"weight": 3}
        )

        c2, _ = Choice.objects.update_or_create(
            source_node=opening,
            target_node=turning_point,
            defaults={
                "display_text": "ადგილზე დარჩენა და რეალობისთვის თვალის გასწორება",
                "order_index": 1,
            },
        )

        c3, _ = Choice.objects.update_or_create(
            source_node=turning_point,
            target_node=hardness_end,
            defaults={
                "display_text": "სიმკაცრე და დისტანცირება",
                "order_index": 0,
            },
        )
        ChoiceTagWeight.objects.update_or_create(
            choice=c3, tag=tag_hardness, defaults={"weight": 3}
        )

        c4, _ = Choice.objects.update_or_create(
            source_node=turning_point,
            target_node=clarity_end,
            defaults={
                "display_text": "სირთულის მიღება და თანაგრძნობის შენარჩუნება",
                "order_index": 1,
            },
        )
        ChoiceTagWeight.objects.update_or_create(
            choice=c4, tag=tag_clarity, defaults={"weight": 3}
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
        if story.status != Story.Status.PUBLISHED:
            story.status = Story.Status.PUBLISHED
            story.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS(f"\n'{story.title}' is published. Refresh /library."))

    def log(self, label, obj, created):
        verb = "Created" if created else "Found existing"
        self.stdout.write(f"{verb} {label}: {obj}")
