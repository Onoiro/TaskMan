from django import forms
from .models import Status
from django.utils.translation import gettext_lazy as _


class StatusForm(forms.ModelForm):

    class Meta:
        model = Status
        fields = ['name', 'description', 'color']

    name = forms.CharField(
        label=_('Name'),
        widget=forms.TextInput(attrs={'placeholder': _('Name')})
    )

    description = forms.CharField(
        label=_('Description'),
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': _('Description'),
            'rows': 3
        }),
        help_text=_('Optional')
    )

    color = forms.CharField(
        label=_('Color'),
        widget=forms.TextInput(attrs={
            'type': 'color',
            'style': 'width: 60px; height: 40px;'
        }),
        help_text=_('Choose status color')
    )
