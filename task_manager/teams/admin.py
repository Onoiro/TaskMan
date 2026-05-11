from django.contrib import admin
from .models import Team, TeamMembership, TeamInvite


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 1
    fields = ('user', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


class TeamInviteInline(admin.TabularInline):
    model = TeamInvite
    extra = 0
    fields = (
        'invite_code', 'created_by', 'expires_at',
        'is_used', 'use_count'
    )
    readonly_fields = (
        'invite_code', 'created_by', 'created_at',
        'is_used', 'used_by', 'used_at', 'use_count'
    )
    can_delete = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('team', 'created_by', 'used_by')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_members_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    inlines = [TeamMembershipInline, TeamInviteInline]

    def get_members_count(self, obj):
        return obj.memberships.count()

    get_members_count.short_description = 'Members'


@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'team', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('user__username', 'team__name')


@admin.register(TeamInvite)
class TeamInviteAdmin(admin.ModelAdmin):
    list_display = (
        'team', 'invite_code', 'created_by',
        'expires_at', 'is_used', 'use_count'
    )
    list_filter = ('is_used', 'expires_at')
    search_fields = (
        'team__name', 'created_by__username',
        'used_by__username'
    )
    readonly_fields = ('invite_code', 'created_at', 'use_count')
    list_select_related = ('team', 'created_by', 'used_by')
