from django import forms
# from django.contrib.auth.models import User
from task_manager.user.models import User
from task_manager.teams.models import Team
from django.utils.translation import gettext_lazy as _


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

    is_team_admin = forms.BooleanField(
        required=False,
        label=_('Register as Team Admin'),
        widget=forms.CheckboxInput(),
        help_text=_("Sign up, then create your team.")
    )

    team_name = forms.CharField(
        required=False,
        label=_('Team Name'),
        help_text=_("Enter team name if you want to join existing team")
    )

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

    def clean(self):
        cleaned_data = super().clean()
        is_team_admin = cleaned_data.get('is_team_admin')
        team_name = cleaned_data.get('team_name')

        if not is_team_admin and not team_name:
            raise forms.ValidationError(_(
                "You must either register as team admin"
                " or specify team name"))

        if is_team_admin and team_name:
            raise forms.ValidationError(_(
                "You can't be team admin and"
                " join existing team at the same time"))

        if team_name and not is_team_admin:
            try:
                team = Team.objects.get(name=team_name)
                cleaned_data['team'] = team
            except Team.DoesNotExist:
                raise forms.ValidationError(_("There is no such team"))

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_team_admin = self.cleaned_data.get('is_team_admin', False)
        if commit:
            user.save()
            if not user.is_team_admin:
                user.team = self.cleaned_data['team']
                user.save()
        return user
