from django import forms
from django.utils.translation import gettext_lazy as _


class FeedbackForm(forms.Form):
    subject = forms.CharField(
        label=_('Specify the subject:'),
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': _('Bug, suggestion, etc.')})
    )
    contact = forms.CharField(
        label=_('* Your email or Telegram (@username):'),
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'email@example.com or @username'})
    )
    message = forms.CharField(
        label=_('* Message:'),
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': _('Describe your issue or suggestion...')
        })
    )
