from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Team, TeamMembership


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'password', 'description']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'password': forms.PasswordInput(
                attrs={'class': 'form-control'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
        }

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 3:
            raise forms.ValidationError(_(
                "Your password is too short."
                " It must contain at least 3 characters."),
                code='min_length')
        return password

    def save(self, commit=True):
        team = super().save(commit=False)
        team.password = self.cleaned_data['password']
        if commit:
            team.save()
        return team


class TeamMemberRoleForm(forms.ModelForm):

    class Meta:
        model = TeamMembership
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_role(self):
        role = self.cleaned_data['role']

        # check if role is valid
        if role not in dict(TeamMembership.ROLE_CHOICES):
            raise forms.ValidationError(_("Invalid role selected."))

        return role
