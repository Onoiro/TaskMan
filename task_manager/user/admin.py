from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    # Добавляем дополнительные поля в админку
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Команда', {'fields': ('is_team_admin', 'team')}),
    )
    
    # дополнительные поля в списке пользователей
    list_display = BaseUserAdmin.list_display + ('is_team_admin', 'team')
    
    # для фильтрации по этим полям
    list_filter = BaseUserAdmin.list_filter + ('is_team_admin', 'team')
    
    # для поиска по этим полям
    search_fields = BaseUserAdmin.search_fields + ('team__name',)

admin.site.register(User, UserAdmin)
