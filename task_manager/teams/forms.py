from django import forms
from task_manager.teams.models import Team
from django.utils.translation import gettext_lazy as _
from .models import TeamMembership


class TeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3}
            ),
        }

    password1 = forms.CharField(
        required=True,
        label=_('Password'),
        widget=forms.PasswordInput(),
        help_text=_("Your password must contain at least 3 characters."))

    password2 = forms.CharField(
        required=True,
        label=_('Confirm password'),
        widget=forms.PasswordInput(),
        help_text=_("Please enter your password one more time"))

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if len(password1) < 3:
            raise forms.ValidationError(_(
                "Your password is too short."
                " It must contain at least 3 characters."),
                code='min_length')
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                _("The entered passwords do not match."))
        return password2

    def save(self, commit=True):
        team = super().save(commit=False)
        team.password = self.cleaned_data['password1']
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
