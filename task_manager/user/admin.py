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
    # Обновляем list_display - убираем старые поля и добавляем новый метод
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'is_staff',
        'get_teams',  # новый метод для отображения команд
        'date_joined'
    )

    # Обновляем list_filter - убираем старые поля
    list_filter = (
        'is_staff', 
        'is_superuser', 
        'is_active', 
        'groups'
    )

    # Добавляем inline для команд
    inlines = [TeamMembershipInline]

    # Добавляем метод для отображения команд пользователя
    def get_teams(self, obj):
        """Показывает список команд пользователя"""
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
    
    # Если у вас есть fieldsets, обновите их тоже
    fieldsets = BaseUserAdmin.fieldsets  # используем стандартные fieldsets

    # Если нужно добавить информацию о командах в детальный просмотр:
    # fieldsets = BaseUserAdmin.fieldsets + (
    #     ('Team Information', {'fields': ()}),  # Здесь можно добавить inline для команд
    # )


admin.site.register(User, UserAdmin)


# class UserAdmin(BaseUserAdmin):
#     # Добавляем дополнительные поля в админку
#     fieldsets = BaseUserAdmin.fieldsets + (
#         ('Команда', {'fields': ('is_team_admin', 'team')}),
#     )

#     # дополнительные поля в списке пользователей
#     list_display = BaseUserAdmin.list_display + ('is_team_admin', 'team')

#     # для фильтрации по этим полям
#     list_filter = BaseUserAdmin.list_filter + ('is_team_admin', 'team')

#     # для поиска по этим полям
#     search_fields = BaseUserAdmin.search_fields + ('team__name',)


# admin.site.register(User, UserAdmin)
