from django import forms
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core import validators
from django.core.exceptions import ValidationError


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username']

    """ Works correct but if password less then 3 chars """
    """ show only help_text message (not message specified in MinLengthValidator """
    """(_("Your password is too short. It must contain at least 3 characters."))) """

    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(
            attrs={'placeholder': _('Password')}),
        help_text=_("Your password must contain at least 3 characters."),
        validators=[
                validators.MinLengthValidator(
                limit_value=3,
                message=_("Your password is too short. "
                          "It must contain at least 3 characters.")
            )])
    
    # password1 = forms.CharField(
    #     label=_('Password'),
    #     widget=forms.PasswordInput(
    #         attrs={'placeholder': _('Password')}),
    #     help_text=_("Your password must contain at least 3 characters."))

    password2 = forms.CharField(
        label=_('Confirm password'),
        widget=forms.PasswordInput(
            attrs={'placeholder': _('Confirm password')}),
        help_text=_("Please enter your password one more time"))
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password1 != password2:
            self.add_error(
                "password2",
                _("The entered passwords do not match."))
        return cleaned_data


    """ Works correct but if password less then 3 chars """
    """ show only help_text message and it's on top of all fields """
    """ (not message specified in raise forms.ValidationError """
    """(_("Your password is too short. It must contain at least 3 characters."))) """

    # def clean(self):
    #     cleaned_data = super().clean()
    #     password1 = cleaned_data.get('password1')
    #     password2 = cleaned_data.get('password2')
    #     if len(password1) < 3:
    #         raise forms.ValidationError(_("Your password is too short. It must contain at least 3 characters."))
    #     if password1 and password1 != password2:
    #         raise ValidationError(_("The entered passwords do not match."))
    #     return cleaned_data

    
    """ Works correct but if password less then 3 chars """
    """ show only help_text message (not message specified in raise ValidationError) """

    # def clean_password1(self):
    #     password1 = self.cleaned_data.get('password1')
    #     if len(password1) < 3:
    #         raise forms.ValidationError(_("Your password is too short. It must contain at least 3 characters."))
    #     return password1
    
    # def clean_password2(self):
    #     password1 = self.cleaned_data.get('password1')
    #     password2 = self.cleaned_data.get('password2')
        
    #     if password1 and password1 != password2:
    #         raise ValidationError(_("The entered passwords do not match."))
    #     return password2


    """ Works correct but if password less then 3 chars """
    """ show only help_text message (not message specified in add_error method) """

    # def clean(self):
    #     cleaned_data = self.cleaned_data
    #     password1 = cleaned_data.get('password1')
    #     password2 = cleaned_data.get('password2')
    #     if len(password1) < 3:
    #         self.add_error(
    #             'password2',
    #             _("Your password is too short. It must contain at least 3 characters."))
    #     if password1 and password1 != password2:
    #         self.add_error(
    #             'password2',
    #         _('The entered passwords do not match.')
    #     )
    #     return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
