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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # if update input password is not required
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = _(
                "Leave blank if you don't want to change password"
            )
            self.fields['password2'].help_text = _(
                "Leave blank if you don't want to change password"
            )

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        # when updating - if the password is empty, skip it
        if self.instance and self.instance.pk and not password1:
            return None
        if password1 and len(password1) < 3:
            raise forms.ValidationError(_(
                "Your password is too short."
                " It must contain at least 3 characters."),
                code='min_length')
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        # when updating - if both are empty, skip
        if (self.instance and self.instance.pk
                and not password1 and not password2):
            return None
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                _("The entered passwords do not match."))
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        # when updating - if one password is filled in and the other is not
        if self.instance and self.instance.pk:
            if (password1 and not password2) or (not password1 and password2):
                raise forms.ValidationError(
                    _("Both password fields must be filled or both left blank")
                )
        return cleaned_data

    def save(self, commit=True):
        team = super().save(commit=False)
        password1 = self.cleaned_data.get('password1')
        # When updating, if the password is not entered, leave the old one
        if password1:
            team.password = password1
        if commit:
            team.save()
        return team


class TeamJoinForm(forms.Form):
    """Form for joining an existing team."""

    name = forms.CharField(
        required=True,
        label=_('Team name'),
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Enter team name')
            }
        ),
    )

    password = forms.CharField(
        required=True,
        label=_('Team password'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Enter team password')
            }
        ),
    )

    def _get_team(self, name):
        """Get team by name or return None."""
        try:
            return Team.objects.get(name=name)
        except Team.DoesNotExist:
            return None

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name
        if not self._get_team(name):
            raise forms.ValidationError(
                _("Team with this name does not exist"))
        return name

    def clean_password(self):
        password = self.cleaned_data.get('password')
        name = self.cleaned_data.get('name')
        if not name or not password:
            return password
        team = self._get_team(name)
        if team and team.password != password:
            raise forms.ValidationError(_("Invalid team password"))
        return password

    def _check_membership(self, user, team):
        """Check if user is already a member or has pending request."""
        from task_manager.teams.models import TeamMembership

        existing = TeamMembership.objects.filter(
            user=user,
            team=team
        ).exists()
        if not existing:
            return None

        pending = TeamMembership.objects.filter(
            user=user,
            team=team,
            status='pending'
        ).exists()
        if pending:
            return _("You already have a pending request to join this team")
        return _("You are already a member of this team")

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        password = cleaned_data.get('password')

        if name and password:
            team = self._get_team(name)
            if team:
                if team.password != password:
                    raise forms.ValidationError(_("Invalid team password"))

                user = self.initial.get('user')
                if user:
                    error = self._check_membership(user, team)
                    if error:
                        raise forms.ValidationError(error)

                cleaned_data['team'] = team

        return cleaned_data


class TeamMemberRoleForm(forms.ModelForm):

    class Meta:
        model = TeamMembership
        fields = ['role', 'status']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_role(self):
        role = self.cleaned_data['role']

        # check if role is valid
        if role not in dict(TeamMembership.ROLE_CHOICES):
            raise forms.ValidationError(_("Invalid role selected."))

        return role

    def clean_status(self):
        status = self.cleaned_data['status']

        # check if status is valid
        if status not in dict(TeamMembership.STATUS_CHOICES):
            raise forms.ValidationError(_("Invalid status selected."))

        return status
