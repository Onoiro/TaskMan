from django import forms
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.statuses.models import Status
from django.utils.translation import gettext_lazy as _


class UserForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']

        help_texts = {
            'first_name': _('Optional'),
            'last_name': _('Optional'),
        }

    password1 = forms.CharField(
        required=True,
        label=_('Password'),
        widget=forms.PasswordInput(),
        help_text=_("Your password must contain at least 3 characters.")
    )

    password2 = forms.CharField(
        required=True,
        label=_('Confirm password'),
        widget=forms.PasswordInput(),
        help_text=_("Please enter your password one more time")
    )

    # Поля для работы с командами (опциональные)
    join_team_name = forms.CharField(
        required=False,
        label=_('Join team (optional)'),
        help_text=_("Enter team name to join an existing team, or leave empty to work individually")
    )

    join_team_password = forms.CharField(
        required=False,
        label=_('Team password'),
        widget=forms.PasswordInput(),
        help_text=_("Required if joining a team")
    )

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        is_update = self.instance and self.instance.pk

        if is_update and not password1:
            return password1

        if password1 and len(password1) < 3:
            raise forms.ValidationError(
                _("Your password is too short. It must contain at least 3 characters."),
                code='min_length'
            )
        return password1

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        is_update = self.instance and self.instance.pk

        if is_update and not password1 and not password2:
            return password2

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                _("The entered passwords do not match.")
            )
        return password2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Если это редактирование существующего пользователя
        if self.instance and self.instance.pk:
            self.fields['password1'].required = False
            self.fields['password2'].required = False
            self.fields['password1'].help_text = _(
                "Leave blank if you don't want to change password"
            )
            self.fields['password2'].help_text = _(
                "Leave blank if you don't want to change password"
            )
            
            # Показываем текущие команды
            memberships = TeamMembership.objects.filter(
                user=self.instance
            ).select_related('team')
            
            if memberships.exists():
                teams_info = []
                for m in memberships:
                    role_str = _("Admin") if m.role == 'admin' else _("Member")
                    teams_info.append(f"{m.team.name} ({role_str})")
                
                # Добавляем read-only поле с информацией о командах
                self.fields['current_teams'] = forms.CharField(
                    label=_('Current teams'),
                    initial=", ".join(teams_info),
                    required=False,
                    widget=forms.TextInput(attrs={'readonly': 'readonly'}),
                )
                # Перемещаем в начало после username
                field_order = ['username', 'current_teams', 'first_name', 'last_name']
                self.order_fields(field_order)
            
            # Меняем подписи для обновления
            self.fields['join_team_name'].label = _('Join another team (optional)')
            self.fields['join_team_name'].help_text = _(
                "Enter team name to join another team, or leave empty"
            )
            
    def clean(self):
        cleaned_data = super().clean()
        join_team_name = cleaned_data.get('join_team_name')
        join_team_password = cleaned_data.get('join_team_password')
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        is_update = self.instance and self.instance.pk

        # Валидация паролей при обновлении
        if is_update:
            if (password1 and not password2) or (not password1 and password2):
                raise forms.ValidationError(
                    _("Both password fields must be filled or both left blank")
                )

        # Валидация команды, если указана
        if join_team_name:
            if not join_team_password:
                raise forms.ValidationError(
                    _("Team password is required when joining a team")
                )
            
            try:
                team = Team.objects.get(name=join_team_name)
                if team.password != join_team_password:
                    raise forms.ValidationError(
                        _("Invalid team password")
                    )
                    
                # Проверяем, не состоит ли уже в этой команде
                if is_update:
                    existing = TeamMembership.objects.filter(
                        user=self.instance,
                        team=team
                    ).exists()
                    if existing:
                        raise forms.ValidationError(
                            _("You are already a member of this team")
                        )
                        
                cleaned_data['team_to_join'] = team
            except Team.DoesNotExist:
                raise forms.ValidationError(
                    _("Team with this name does not exist")
                )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Устанавливаем пароль только если он был введен
        password1 = self.cleaned_data.get('password1')
        if password1:
            user.set_password(password1)

        is_new_user = user.pk is None

        if commit:
            user.save()
            
            # Обработка присоединения к команде
            team = self.cleaned_data.get('team_to_join')
            if team:
                TeamMembership.objects.create(
                    user=user,
                    team=team,
                    role='member'
                )
            
            # Создаем дефолтные статусы для новых пользователей
            # (только если не присоединились к команде)
            if is_new_user and not team:
                Status.create_default_statuses_for_user(user)

        return user

# class UserForm(forms.ModelForm):

#     class Meta:
#         model = User
#         fields = ['username', 'first_name', 'last_name']

#         help_texts = {
#             'first_name': _('Optional'),
#             'last_name': _('Optional'),
#         }

#     is_team_admin = forms.BooleanField(
#         required=False,
#         label=_('Register as Team Admin'),
#         widget=forms.CheckboxInput(),
#         help_text=_("Sign up, then create your team.")
#     )

#     team_name = forms.CharField(
#         required=False,
#         label=_('Join Team'),
#         help_text=_("Enter team name if you want to join existing team")
#     )

#     password1 = forms.CharField(
#         required=True,
#         label=_('Password'),
#         widget=forms.PasswordInput(),
#         help_text=_("Your password must contain at least 3 characters."))

#     password2 = forms.CharField(
#         required=True,
#         label=_('Confirm password'),
#         widget=forms.PasswordInput(),
#         help_text=_("Please enter your password one more time"))

#     def clean_password1(self):
#         password1 = self.cleaned_data.get('password1')
#         is_update = self.instance and self.instance.pk

#         # validation no need if update and no password entered
#         if is_update and not password1:
#             return password1

#         if len(password1) < 3:
#             raise forms.ValidationError(_(
#                 "Your password is too short."
#                 " It must contain at least 3 characters."),
#                 code='min_length')
#         return password1

#     def clean_password2(self):
#         password1 = self.cleaned_data.get('password1')
#         password2 = self.cleaned_data.get('password2')
#         is_update = self.instance and self.instance.pk

#         # validation no need if update and no passwords entered
#         if is_update and not password1 and not password2:
#             return password2

#         if password1 and password2 and password1 != password2:
#             raise forms.ValidationError(
#                 _("The entered passwords do not match."))
#         return password2

#     # Override the form constructor to add my logic
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # if this is editing an existing user (the user has a pk)
#         if self.instance and self.instance.pk:
#             self.fields['password1'].required = False
#             self.fields['password2'].required = False
#             self.fields['password1'].help_text = _(
#                 "Leave blank if you don't want to change password"
#             )
#             self.fields['password2'].help_text = _(
#                 "Leave blank if you don't want to change password"
#             )
#             if self.instance.team:
#                 # set initial value for team_name field
#                 self.initial['team_name'] = self.instance.team.name
#                 # The readonly attribute (it does not prevent data transfer,
#                 # but tells the user that the field cannot be changed)
#                 readonly_attr = {'readonly': 'readonly'}
#                 self.fields['team_name'].widget.attrs.update(readonly_attr)
#                 # The is_team_admin field is hidden
#                 # so that the value does not change
#                 self.fields['is_team_admin'].widget = forms.HiddenInput()
#             elif self.instance.is_team_admin:
#                 # If the user is a team admin, hide the team_name field
#                 self.fields['team_name'].widget = forms.HiddenInput()
#                 self.initial['is_team_admin'] = True

#     def clean(self):
#         cleaned_data = super().clean()
#         is_update = self.instance and self.instance.pk
#         is_team_admin = cleaned_data.get('is_team_admin')
#         team_name = cleaned_data.get('team_name')
#         password1 = cleaned_data.get('password1')
#         password2 = cleaned_data.get('password2')

#         # additional passwords validation if only one field of password entered
#         if is_update:
#             if (password1 and not password2) or (not password1 and password2):
#                 raise forms.ValidationError(
#                     _("Both password fields must be filled or both left blank")
#                 )

#         if is_update and (self.instance.team or self.instance.is_team_admin):
#             return self._clean_update(cleaned_data)
#         else:
#             self._validate_team_admin_and_team_name(is_team_admin, team_name)
#             self._associate_team(team_name, cleaned_data)

#         return cleaned_data

#     def _clean_update(self, cleaned_data):
#         # set values from the instance to avoid incorrect validation
#         cleaned_data['is_team_admin'] = self.instance.is_team_admin
#         # If user already has a team, team_name is taken from it,
#         # otherwise it is cleared
#         cleaned_data['team'] = (
#             self.instance.team
#             if self.instance.team
#             else None
#         )
#         cleaned_data['team_name'] = (
#             self.instance.team.name
#             if self.instance.team
#             else ''
#         )
#         return cleaned_data

#     def _validate_team_admin_and_team_name(self, is_team_admin, team_name):
#         if is_team_admin and team_name:
#             raise forms.ValidationError(_(
#                 "You can't signup as team admin and"
#                 " join existing team at the same time"
#             ))

#     def _associate_team(self, team_name, cleaned_data):
#         # Associating a user with an existing team
#         if team_name:
#             try:
#                 team = Team.objects.get(name=team_name)
#                 cleaned_data['team'] = team
#             except Team.DoesNotExist:
#                 raise forms.ValidationError(_("There is no such team"))

#     def save(self, commit=True):
#         user = super().save(commit=False)
#         # set password only if it was entered
#         password1 = self.cleaned_data.get('password1')
#         if password1:
#             user.set_password(password1)

#         user.is_team_admin = self.cleaned_data.get('is_team_admin', False)

#         is_new_user = user.pk is None

#         if commit:
#             user.save()
#             team_name = self.cleaned_data.get('team_name')
#             if not user.is_team_admin and team_name:
#                 user.team = self.cleaned_data['team']
#                 user.save()

#         # set default statuses for new user
#         if is_new_user:
#             Status.create_default_statuses_for_user(user)

#         return user
