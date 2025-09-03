from django.contrib.auth.models import AbstractUser
# from django.db import models


class User(AbstractUser):
    # is_team_admin = models.BooleanField(default=False)
    # team = models.ForeignKey(
    #     'teams.Team',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='team_members'
    # )

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

    # def get_teams(self):
    #     """Получить все команды пользователя"""
    #     return self.team_memberships.select_related('team')

    # def is_admin_of_team(self, team):
    #     """Проверить, является ли пользователь админом команды"""
    #     membership = self.team_memberships.filter(team=team).first()
    #     return membership.role == 'admin' if membership else False

    # def user_str(self):
    #     return (f"{self.first_name} {self.last_name}")


# AbstractUser.__str__ = user_str
