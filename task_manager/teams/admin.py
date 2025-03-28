from django.contrib import admin
from .models import Team


class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'team_admin', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description', 'team_admin__username')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('name', 'team_admin')
        }),
        ('Дополнительная информация', {
            'fields': ('description', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('team_admin')


admin.site.register(Team, TeamAdmin)
