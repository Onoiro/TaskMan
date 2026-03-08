import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    description = models.TextField(
        verbose_name=_('Description'),
        blank=True,
        default=''
    )
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    @property
    def display_name(self):
        if self.is_deleted:
            return _('Deleted user')
        return self.username

    def soft_delete(self):
        """
        Soft delete the user, deactivating the account and anonymizing the username.
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.is_active = False
        
        # Anonymize username to free it up for reuse
        unique_suffix = uuid.uuid4().hex[:8]
        self.username = f"deleted_{self.id}_{unique_suffix}"
        self.set_unusable_password()
        self.save()

        # 1. Remove from executors in all tasks
        self.executor_tasks.clear()

        # 2. Handle TeamMemberships and Teams
        memberships = self.team_memberships.all()
        for membership in memberships:
            team = membership.team
            if membership.role == 'admin':
                # Check for other active admins or members
                other_memberships = team.memberships.exclude(user=self).filter(status='active')
                
                if other_memberships.exists():
                    # Promote the next member to admin
                    next_admin = other_memberships.order_by('joined_at').first()
                    next_admin.role = 'admin'
                    next_admin.save()
                else:
                    # No other active members, delete the team
                    team.delete()
                    continue # Team is gone, membership is gone by CASCADE

            # Deactivate membership
            membership.status = 'inactive'
            membership.save()
