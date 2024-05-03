from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.core import validators


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput,
        help_text=_("Your password must contain at least 3 characters."),
        validators=[
            validators.MinLengthValidator(
                limit_value=3,
                message=_("Your password is too short. "
                          "It must contain at least 3 characters.")
            )])
    password2 = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput,
        help_text=_("Please enter your password one more time"))

    def clean_password2(self):
        cleaned_data = self.cleaned_data
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password1 != password2:
            self.add_error(
                'password2',
                _('The entered passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
