from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator
from django.core.exceptions import ValidationError


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(
            attrs={'placeholder': _('Password')}),
        help_text=_("Your password must contain at least 3 characters."),
        # validators=[MinLengthValidator(3, message=_("Your password is too short. It must contain at least 3 characters."))],
        # error_messages={'min_length': _("Your password is too short. It must contain at least 3 characters.")}
        )

    password2 = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput(
            attrs={'placeholder': _('Confirm password')}),
        help_text=_("Please enter your password one more time"))
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        print(password1)
        # if len(password1) < 3:
        #     raise forms.ValidationError('', code='min_length')
        if len(password1) < 3:
            print(len(password1))
            raise forms.ValidationError(
                _("Your password is too short. It must contain at least 3 characters."))
        return password1
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("The entered passwords do not match."))
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
