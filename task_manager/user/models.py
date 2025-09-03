from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    def user_str(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_teams(self):
        """Получить все команды пользователя через TeamMembership"""
        from task_manager.teams.models import TeamMembership
        return TeamMembership.objects.filter(user=self).select_related('team')
    
    def is_admin_of_team(self, team):
        """Проверить, является ли пользователь админом команды"""
        from task_manager.teams.models import TeamMembership
        try:
            membership = TeamMembership.objects.get(user=self, team=team)
            return membership.role == 'admin'
        except TeamMembership.DoesNotExist:
            return False
