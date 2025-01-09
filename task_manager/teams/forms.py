from django import forms
from task_manager.teams.models import Team
from django.utils.translation import gettext_lazy as _


class TeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = ['name', 'description']

    def save(self, commit=True):
        team = super().save(commit=False)
        if commit:
            team.save()
        return team
