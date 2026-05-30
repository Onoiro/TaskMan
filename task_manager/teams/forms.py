from django import forms
from task_manager.teams.models import Team
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxLengthValidator
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

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Description')
        }),
        help_text=_('Optional'),
        validators=[MaxLengthValidator(20000)]
    )

    password1 = forms.CharField(
        required=True,
        label=_('Password'),
        widget=forms.PasswordInput(),
        help_text=_("Your password must contain at least 8 characters."))

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
        if password1 and len(password1) < 8:
            raise forms.ValidationError(_(
                "Your password is too short."
                " It must contain at least 8 characters."),
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

    invite_link = forms.CharField(
        required=False,
        label=_('Invite link'),
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Paste invite link here')
            }
        ),
        help_text=_(
            "If you have an invite link, paste it here. "
            "Otherwise, enter team name and password below."
        ),
    )

    name = forms.CharField(
        required=False,
        label=_('Team name'),
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': _('Enter team name')
            }
        ),
    )

    password = forms.CharField(
        required=False,
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

    def _get_invite_from_link(self, link):
        """Extract invite code from link and return invite object."""
        from task_manager.teams.models import TeamInvite
        from django.utils import timezone

        if not link:
            return None

        # Extract invite code from URL
        # Expected formats:
        # - https://taskman.tech/teams/join-invite/<uuid>/
        # - <uuid>
        try:
            # Try to extract UUID from URL
            if '/teams/join-invite/' in link:
                parts = link.split('/teams/join-invite/')
                if len(parts) > 1:
                    code_part = parts[1].rstrip('/').split('/')[0]
                else:
                    return None
            elif 'join-invite/' in link:
                parts = link.split('join-invite/')
                if len(parts) > 1:
                    code_part = parts[1].rstrip('/').split('/')[0]
                else:
                    return None
            else:
                # Try to use as direct UUID
                code_part = link.strip()

            # Validate UUID format
            import uuid
            invite_code = uuid.UUID(code_part)

            # Get invite
            invite = TeamInvite.objects.get(invite_code=invite_code)

            # Validate invite
            if invite.is_used:
                return None
            if not invite.is_valid():
                return None
            if invite.use_count >= invite.max_uses:
                return None

            return invite
        except (ValueError, TeamInvite.DoesNotExist):
            return None

    def clean_invite_link(self):
        invite_link = self.cleaned_data.get('invite_link', '').strip()
        if invite_link:
            invite = self._get_invite_from_link(invite_link)
            if invite:
                self.cleaned_data['_invite'] = invite
            else:
                raise forms.ValidationError(
                    _("Invalid or expired invite link")
                )
        return invite_link

    def clean_name(self):
        name = self.cleaned_data.get('name')
        invite = self.cleaned_data.get('_invite')

        # If using invite link, skip name validation
        if invite:
            return name

        if not name:
            raise forms.ValidationError(
                _("Team name is required when not using invite link")
            )

        team = self._get_team(name)
        if not team:
            raise forms.ValidationError(
                _("Team with this name does not exist"))
        return name

    def clean_password(self):
        password = self.cleaned_data.get('password')
        invite = self.cleaned_data.get('_invite')

        # If using invite link, skip password validation
        if invite:
            return password

        name = self.cleaned_data.get('name')
        if not name or not password:
            raise forms.ValidationError(
                _("Team password is required when not using invite link")
            )

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
        invite = cleaned_data.get('_invite')
        name = cleaned_data.get('name')
        password = cleaned_data.get('password')
        user = self.initial.get('user')

        if invite:
            # Using invite link
            team = invite.team
            if user:
                error = self._check_membership(user, team)
                if error:
                    raise forms.ValidationError(error)
            cleaned_data['team'] = team
        elif name and password:
            # Using team name and password
            team = self._get_team(name)
            if team:
                if team.password != password:
                    raise forms.ValidationError(_("Invalid team password"))

                if user:
                    error = self._check_membership(user, team)
                    if error:
                        raise forms.ValidationError(error)

                cleaned_data['team'] = team
        else:
            raise forms.ValidationError(
                _("Either provide an invite link or team name and password")
            )

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
