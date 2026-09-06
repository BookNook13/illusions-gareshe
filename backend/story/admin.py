from django.contrib import admin

from .models import (
    Bookmark,
    Choice,
    ChoiceTagWeight,
    Interpretation,
    PsychologicalTag,
    ReaderChoice,
    ReadingSession,
    Reflection,
    Story,
    StoryNode,
    StoryTheme,
    StoryVersion,
)


class ChoiceTagWeightInline(admin.TabularInline):
    model = ChoiceTagWeight
    extra = 1


class ChoiceInline(admin.TabularInline):
    model = Choice
    fk_name = "source_node"
    fields = ("display_text", "target_node", "order_index", "requires_flag")
    extra = 1
    show_change_link = True


class StoryVersionInline(admin.TabularInline):
    model = StoryVersion
    extra = 0
    fields = ("version_number", "is_published", "published_at", "root_node")
    readonly_fields = ("published_at",)
    show_change_link = True


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "estimated_minutes")
    list_filter = ("status", "themes")
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("themes",)
    inlines = [StoryVersionInline]


@admin.register(StoryTheme)
class StoryThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


@admin.register(StoryVersion)
class StoryVersionAdmin(admin.ModelAdmin):
    list_display = ("story", "version_number", "is_published", "published_at", "root_node")
    list_filter = ("is_published", "story")
    search_fields = ("story__title",)
    actions = ["publish_versions", "validate_versions"]

    @admin.action(description="Publish selected versions")
    def publish_versions(self, request, queryset):
        for version in queryset:
            version.publish()

    @admin.action(description="Validate story graph")
    def validate_versions(self, request, queryset):
        for version in queryset:
            problems = version.validate_graph()
            if problems:
                self.message_user(request, f"{version}: {'; '.join(problems)}", level="ERROR")
            else:
                self.message_user(request, f"{version}: graph is valid.")


@admin.register(StoryNode)
class StoryNodeAdmin(admin.ModelAdmin):
    list_display = ("chapter_title", "slug", "story_version", "node_type", "is_ending", "order_index")
    list_filter = ("node_type", "is_ending", "story_version__story")
    search_fields = ("chapter_title", "slug", "text_content")
    inlines = [ChoiceInline]
    autocomplete_fields = ("story_version",)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("display_text", "source_node", "target_node", "order_index")
    list_filter = ("source_node__story_version__story",)
    search_fields = ("display_text",)
    autocomplete_fields = ("source_node", "target_node")
    inlines = [ChoiceTagWeightInline]


@admin.register(PsychologicalTag)
class PsychologicalTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category")
    list_filter = ("category",)
    search_fields = ("name", "slug")


@admin.register(ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "story_version", "run_number", "is_completed", "last_active_at")
    list_filter = ("is_completed", "story_version__story")
    readonly_fields = ("psychological_profile", "flags")
    search_fields = ("user__username", "user__email")


@admin.register(ReaderChoice)
class ReaderChoiceAdmin(admin.ModelAdmin):
    list_display = ("reading_session", "choice", "made_at")
    readonly_fields = ("reading_session", "choice", "node_at_time", "made_at")
    list_filter = ("made_at",)


@admin.register(Interpretation)
class InterpretationAdmin(admin.ModelAdmin):
    list_display = ("reading_session", "tag", "weight", "created_at")
    list_filter = ("tag",)


@admin.register(Reflection)
class ReflectionAdmin(admin.ModelAdmin):
    list_display = ("reading_session", "strongest_tag", "generated_at")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("user", "story", "node", "created_at")
