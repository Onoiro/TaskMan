from django import forms
from .models import Status
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxLengthValidator


class StatusForm(forms.ModelForm):

    class Meta:
        model = Status
        fields = ['name', 'description', 'color', 'is_completed']

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
        help_text=_('Optional'),
        validators=[MaxLengthValidator(20000)]
    )

    color = forms.CharField(
        label=_('Color'),
        widget=forms.TextInput(attrs={
            'type': 'color',
            'style': 'width: 60px; height: 40px;'
        }),
        help_text=_('Choose status color')
    )

    is_completed = forms.BooleanField(
        label=_('Final status'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text=_(
            'Tasks with a final status are hidden from the default '
            'task list'
        )
    )
