from django.contrib import admin

from .models import (
    Choice,
    ChoiceLog,
    ChoiceTagWeight,
    PsychologicalTag,
    ReaderProgress,
    StoryNode,
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


@admin.register(StoryNode)
class StoryNodeAdmin(admin.ModelAdmin):
    list_display = ("chapter_title", "slug", "node_type", "is_start", "is_ending", "order_index")
    list_filter = ("node_type", "is_ending", "is_start", "chapter_title")
    search_fields = ("chapter_title", "slug", "text_content")
    inlines = [ChoiceInline]
    prepopulated_fields = {"slug": ("chapter_title",)}


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("display_text", "source_node", "target_node", "order_index")
    list_filter = ("source_node__chapter_title",)
    search_fields = ("display_text",)
    autocomplete_fields = ("source_node", "target_node")
    inlines = [ChoiceTagWeightInline]


@admin.register(PsychologicalTag)
class PsychologicalTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category")
    list_filter = ("category",)
    search_fields = ("name", "slug")


@admin.register(ReaderProgress)
class ReaderProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "current_node", "is_completed", "last_active_at")
    list_filter = ("is_completed",)
    readonly_fields = ("psychological_profile", "flags")
    search_fields = ("user__username", "user__email")


@admin.register(ChoiceLog)
class ChoiceLogAdmin(admin.ModelAdmin):
    list_display = ("reader_progress", "choice", "made_at")
    readonly_fields = ("reader_progress", "choice", "node_at_time", "made_at")
    list_filter = ("made_at",)
