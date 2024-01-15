from django import forms
from .models import User
from django.core.exceptions import ValidationError
from django.contrib import messages



class UserForm(forms.ModelForm):
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label="Подтверждение пароля"
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password != password_confirm:
            self.add_error('password_confirm', "The entered passwords do not match.")
            # raise ValidationError("Пароли не совпадают")

        return cleaned_data
