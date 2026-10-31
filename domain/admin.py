"""Django admin: browse the nights, arrivals and scares (TV and phone, every person) in production at /admin."""
from django.contrib import admin
from django.db.models import Count

from domain.entities import Arrival, Night, ScareEvent

admin.site.site_header = "Scare-TV · night log"
admin.site.site_title = "Scare-TV"
admin.site.index_title = "Numbers only: no images, no sound"


def source(night):
    return "📱 phone" if night.media == "web" else "📺 TV"


class ScareInline(admin.TabularInline):
    model = ScareEvent
    extra = 0
    fields = ("created_at", "kind", "name", "face_seen", "flinch", "fled", "wait_seconds", "trigger", "false_alarm")
    readonly_fields = ("created_at", "kind", "name", "face_seen", "flinch", "fled", "wait_seconds", "trigger")
    show_change_link = True


@admin.register(Night)
class NightAdmin(admin.ModelAdmin):
    list_display = ("started_at", "where", "media", "lang", "minutes", "n_arrivals", "n_scares")
    list_filter = ("media", "lang")
    date_hierarchy = "started_at"
    inlines = [ScareInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_scares=Count("scares", distinct=True), _arrivals=Count("arrivals", distinct=True))

    @admin.display(description="where")
    def where(self, obj):
        return source(obj)

    @admin.display(description="arrivals", ordering="_arrivals")
    def n_arrivals(self, obj):
        return obj._arrivals

    @admin.display(description="scares", ordering="_scares")
    def n_scares(self, obj):
        return obj._scares


@admin.register(ScareEvent)
class ScareEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "where", "kind", "name", "flinch", "fled", "face_seen", "wait_seconds", "trigger", "false_alarm")
    list_filter = ("night__media", "kind", "fled", "false_alarm", "trigger", "name")
    list_editable = ("false_alarm",)
    search_fields = ("name",)
    date_hierarchy = "created_at"
    list_select_related = ("night",)
    readonly_fields = ("night", "kind", "name", "face_seen", "flinch", "fled", "wait_seconds", "trigger", "created_at")
    list_per_page = 100

    @admin.display(description="where", ordering="night__media")
    def where(self, obj):
        return source(obj.night)


@admin.register(Arrival)
class ArrivalAdmin(admin.ModelAdmin):
    list_display = ("created_at", "night")
    date_hierarchy = "created_at"
    list_select_related = ("night",)
