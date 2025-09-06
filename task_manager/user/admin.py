from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User
from task_manager.teams.models import TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0
    verbose_name = "Team Membership"
    verbose_name_plural = "Team Memberships"
    fields = ('team', 'role', 'joined_at')
    readonly_fields = ('joined_at',)


class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'get_teams',
        'date_joined'
    )

    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'groups'
    )

    inlines = [TeamMembershipInline]

    def get_teams(self, obj):
        """Show list of teams"""
        memberships = obj.team_memberships.select_related('team').all()
        if not memberships:
            return "No teams"

        teams_info = []
        for membership in memberships:
            if membership.role == 'admin':
                teams_info.append(f"{membership.team.name} (admin)")
            else:
                teams_info.append(membership.team.name)
        return ", ".join(teams_info)

    get_teams.short_description = 'Teams'

    fieldsets = BaseUserAdmin.fieldsets

    # If need to add team info in team detail
    # fieldsets = BaseUserAdmin.fieldsets + (
    #     ('Team Information', {'fields': ()}),
    # )


admin.site.register(User, UserAdmin)
