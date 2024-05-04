from django import forms
from .models import Status
from django.utils.translation import gettext_lazy as _


class StatusForm(forms.ModelForm):

    class Meta:
        model = Status
        fields = ['name']

    name = forms.CharField(
        label=_('Name'),
        widget=forms.TextInput(attrs={'placeholder': _('Name')})
    )
