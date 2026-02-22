from django import forms
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.statuses.models import Status
from django.utils.translation import gettext_lazy as _


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'description']

        help_texts = {
            'first_name': _('Optional'),
            'last_name': _('Optional'),
            'description': _('Optional'),
        }

    password1 = forms.CharField(
        required=True,
        label=_('Password'),
        widget=forms.PasswordInput(),
        help_text=_("Your password must contain at least 3 characters.")
    )

    password2 = forms.CharField(
        required=True,
        label=_('Confirm password'),
        widget=forms.PasswordInput(),
        help_text=_("Please enter your password one more time")
    )

    join_team_name = forms.CharField(
        required=False,
        label=_('Join team (optional)'),
        help_text=_(
            "Enter team name to join an existing team,"
            " or leave empty to work individually")
    )

    join_team_password = forms.CharField(
        required=False,
        label=_('Team password'),
        widget=forms.PasswordInput(),
        help_text=_("Required if joining a team")
    )

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        is_update = self.instance and self.instance.pk

        if is_update and not password1:
            return None

        if password1 and len(password1) < 3:
            raise forms.ValidationError(
                _("Your password is too short."
                  " It must contain at least 3 characters."),
                code='min_length'
            )
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        is_update = self.instance and self.instance.pk

        if is_update and not password1 and not password2:
            return None

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                _("The entered passwords do not match.")
            )
        return password2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # if updating exist user
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = _(
                "Leave blank if you don't want to change password"
            )
            self.fields['password2'].help_text = _(
                "Leave blank if you don't want to change password"
            )

            # show user's current teams
            memberships = TeamMembership.objects.filter(
                user=self.instance
            ).select_related('team')

            if memberships.exists():
                teams_info = []
                for m in memberships:
                    role_str = (_("Admin") if m.role == 'admin'
                                else _("Member"))
                    teams_info.append(f"{m.team.name} ({role_str})")

                # add read-only field with current teams info
                self.fields['current_teams'] = forms.CharField(
                    label=_('Current teams'),
                    initial=", ".join(teams_info),
                    required=False,
                    widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                )
                # set field after username
                field_order = [
                    'username',
                    'current_teams',
                    'first_name',
                    'last_name'
                ]
                self.order_fields(field_order)

            # set fields labels
            self.fields['join_team_name'].label = _(
                'Join another team (optional)')
            self.fields['join_team_name'].help_text = _(
                "Enter team name to join another team, or leave empty"
            )

    def _validate_passwords(self, cleaned_data, is_update):
        """Validate password fields for updates."""
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if is_update:
            if (password1 and not password2) or (not password1 and password2):
                raise forms.ValidationError(
                    _("Both password fields must be filled or both left blank")
                )

    def _validate_team(self, cleaned_data, is_update):
        """Validate team joining logic."""
        join_team_name = cleaned_data.get('join_team_name')
        join_team_password = cleaned_data.get('join_team_password')

        if not join_team_name:
            return

        self._validate_team_password(join_team_password)
        team = self._get_team_by_name(join_team_name)
        self._validate_team_credentials(team, join_team_password)

        if is_update:
            self._check_existing_membership(team)

        cleaned_data['team_to_join'] = team

    def _validate_team_password(self, join_team_password):
        """Check if team password is provided."""
        if not join_team_password:
            raise forms.ValidationError(
                _("Team password is required when joining a team")
            )

    def _get_team_by_name(self, team_name):
        """Get team by name or raise validation error."""
        try:
            return Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            raise forms.ValidationError(
                _("Team with this name does not exist")
            )

    def _validate_team_credentials(self, team, password):
        """Validate team password."""
        if team.password != password:
            raise forms.ValidationError(
                _("Invalid team password")
            )

    def _check_existing_membership(self, team):
        """Check if user is already a member of the team."""
        existing = TeamMembership.objects.filter(
            user=self.instance,
            team=team
        ).exists()
        if existing:
            raise forms.ValidationError(
                _("You are already a member of this team")
            )

    def clean(self):
        cleaned_data = super().clean()
        is_update = self.instance and self.instance.pk

        self._validate_passwords(cleaned_data, is_update)
        self._validate_team(cleaned_data, is_update)

        return cleaned_data

    def save(self, commit=True, request=None):
        user = super().save(commit=False)

        # set password only if it inputed
        password1 = self.cleaned_data.get('password1')
        if password1:
            user.set_password(password1)

        is_new_user = user.pk is None

        if commit:
            user.save()

            # handling join team
            team = self.cleaned_data.get('team_to_join')
            if team:
                TeamMembership.objects.create(
                    user=user,
                    team=team,
                    role='member'
                )

            # create default statuses for new users
            # only if they didn't join any team
            if is_new_user and not team:
                Status.create_default_statuses_for_user(user)

        return user
