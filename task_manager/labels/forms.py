from django import forms
from task_manager.labels.models import Label
from django.utils.translation import gettext_lazy as _


class LabelForm(forms.ModelForm):

    class Meta:
        model = Label
        fields = ['name']
    
    name = forms.CharField(
        label=_('Name'),
        widget=forms.TextInput(attrs={'placeholder': _('Name')})
    )
