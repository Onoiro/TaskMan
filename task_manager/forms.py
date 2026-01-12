from django import forms
from django.utils.translation import gettext_lazy as _


class FeedbackForm(forms.Form):
    subject = forms.CharField(
        label=_('Specify the subject:'),
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': _('Bug, suggestion, etc.')})
    )
    email = forms.EmailField(
        label=_('* Your email address (or Telegram):'),
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com or @username'})
    )
    message = forms.CharField(
        label=_('* Message:'),
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': _('Describe your issue or suggestion...')
        })
    )
