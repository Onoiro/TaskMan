from django.contrib import admin
from .models import Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_members_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    inlines = [TeamMembershipInline]

    def get_members_count(self, obj):
        return obj.memberships.count()

    get_members_count.short_description = 'Members'


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'team__name')
