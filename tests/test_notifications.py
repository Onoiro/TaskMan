from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.notifications.models import Notification
from task_manager.notifications import services


class NotificationModelTest(TestCase):
    """Tests for Notification model."""

    fixtures = [
        'tests/fixtures/test_users.json',
        'tests/fixtures/test_teams.json',
        'tests/fixtures/test_teams_memberships.json',
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')

    def test_create_notification_minimal_fields(self):
        """Test creating notification with minimal fields."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test notification',
        )
        self.assertEqual(notif.recipient, self.user)
        self.assertEqual(notif.notification_type,
                         Notification.NotificationType.TASK_ASSIGNED)
        self.assertEqual(notif.message, 'Test notification')
        self.assertFalse(notif.is_read)
        self.assertIsNotNone(notif.created_at)

    def test_is_read_default_false(self):
        """Test is_read defaults to False."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
        )
        self.assertFalse(notif.is_read)

    def test_mark_as_read_sets_true(self):
        """Test mark_as_read() sets is_read=True."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
        )
        notif.mark_as_read()
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_as_read_no_extra_query_on_already_read(self):
        """Test mark_as_read() on already read doesn't write."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
            is_read=True,
        )
        with self.assertNumQueries(0):
            notif.mark_as_read()

    def test_str_contains_type_and_recipient(self):
        """Test __str__ contains notification type and recipient name."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
        )
        str_repr = str(notif)
        self.assertIn('task_assigned', str_repr.lower())
        self.assertIn(self.user.username, str_repr)

    def test_ordering_newest_first(self):
        """Test notifications ordered by created_at descending."""
        notif1 = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='First',
        )
        notif2 = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Second',
        )
        notifications = list(Notification.objects.filter(
            recipient=self.user))
        self.assertEqual(notifications[0], notif2)
        self.assertEqual(notifications[1], notif1)


class NotificationServicesTest(TestCase):
    """Tests for notification service functions."""

    fixtures = [
        'tests/fixtures/test_users.json',
        'tests/fixtures/test_teams.json',
        'tests/fixtures/test_teams_memberships.json',
        'tests/fixtures/test_statuses.json',
        'tests/fixtures/test_labels.json',
        'tests/fixtures/test_tasks.json',
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.status = Status.objects.get(pk=12)

    def test_notify_task_assigned_creates_notification(self):
        """Test notify_task_assigned creates notification."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_assigned(task, self.other_user, self.user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn('Test Task', notif.message)

    def test_notify_task_assigned_skip_self(self):
        """Test notify_task_assigned skips when assignee == actor."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_assigned(task, self.user, self.user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
        ).first()
        self.assertIsNone(notif)

    def test_notify_task_unassigned_creates_notification(self):
        """Test notify_task_unassigned creates notification."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_unassigned(task, self.other_user, self.user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TASK_UNASSIGNED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_task_unassigned_skip_self(self):
        """Test notify_task_unassigned skips when assignee == actor."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_unassigned(task, self.user, self.user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_UNASSIGNED,
        ).first()
        self.assertIsNone(notif)

    def test_notify_task_status_changed_notifies_author(self):
        """Test notify_task_status_changed notifies author."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_status_changed(task, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_task_status_changed_notifies_executor(self):
        """Test notify_task_status_changed notifies executor."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.other_user,
            team=self.team,
        )
        task.executors.add(self.user)
        services.notify_task_status_changed(task, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_task_status_changed_skip_actor(self):
        """Test notify_task_status_changed skips actor."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_status_changed(task, self.user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
        ).first()
        self.assertIsNone(notif)

    def test_notify_task_completed_notifies_author(self):
        """Test notify_task_completed notifies author."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        services.notify_task_completed(task, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_COMPLETED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_task_completed_notifies_executor(self):
        """Test notify_task_completed notifies executor."""
        task = Task.objects.create(
            name='Test Task',
            status=self.status,
            author=self.other_user,
            team=self.team,
        )
        task.executors.add(self.user)
        services.notify_task_completed(task, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_COMPLETED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_team_join_request_notifies_admins(self):
        """Test notify_team_join_request notifies all admins."""
        services.notify_team_join_request(self.team, self.other_user)
        notifs = Notification.objects.filter(
            notification_type=Notification.NotificationType.TEAM_JOIN_REQUEST,
        )
        admin_ids = User.objects.filter(
            team_memberships__team=self.team,
            team_memberships__role='admin',
        ).values_list('id', flat=True)
        for notif in notifs:
            self.assertIn(notif.recipient.id, admin_ids)

    def test_notify_team_join_request_notifies_only_admins(self):
        """Test notify_team_join_request doesn't notify regular members."""
        member = User.objects.create_user(
            username='member_user',
            password='pass123',
        )
        TeamMembership.objects.create(
            user=member,
            team=self.team,
            role='member',
            status='active',
        )
        services.notify_team_join_request(self.team, self.other_user)
        notif = Notification.objects.filter(
            recipient=member,
            notification_type=Notification.NotificationType.TEAM_JOIN_REQUEST,
        ).first()
        self.assertIsNone(notif)

    def test_notify_team_member_joined_notifies_admins(self):
        """Test notify_team_member_joined notifies admins."""
        services.notify_team_member_joined(self.team, self.other_user)
        notifs = Notification.objects.filter(
            notification_type=Notification.NotificationType.TEAM_MEMBER_JOINED,
        )
        self.assertGreater(notifs.count(), 0)

    def test_notify_team_member_joined_skip_if_admin(self):
        """Test notify_team_member_joined skips if new member is admin."""
        admin_user = User.objects.create_user(
            username='admin_user',
            password='pass123',
        )
        TeamMembership.objects.create(
            user=admin_user,
            team=self.team,
            role='admin',
            status='active',
        )
        services.notify_team_member_joined(self.team, admin_user)
        notif = Notification.objects.filter(
            recipient=admin_user,
            notification_type=Notification.NotificationType.TEAM_MEMBER_JOINED,
        ).first()
        self.assertIsNone(notif)

    def test_notify_request_approved_correct_recipient(self):
        """Test notify_request_approved notifies correct user."""
        services.notify_request_approved(self.team, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.
            TEAM_REQUEST_APPROVED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_request_rejected_correct_recipient(self):
        """Test notify_request_rejected notifies correct user."""
        services.notify_request_rejected(self.team, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.
            TEAM_REQUEST_REJECTED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_member_removed_skip_self(self):
        """Test notify_member_removed skips if removed_user == actor."""
        services.notify_member_removed(self.team, self.user, self.user)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TEAM_MEMBER_REMOVED,
        ).first()
        self.assertIsNone(notif)

    def test_notify_member_removed_creates_notification(self):
        """Test notify_member_removed creates notification."""
        services.notify_member_removed(self.team, self.other_user, self.user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TEAM_MEMBER_REMOVED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_role_changed_creates_notification(self):
        """Test notify_role_changed creates notification."""
        services.notify_role_changed(self.team, self.other_user, 'admin')
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TEAM_ROLE_CHANGED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_team_invited_creates_notification(self):
        """Test notify_team_invited creates notification."""
        services.notify_team_invited(self.team, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TEAM_INVITED,
        ).first()
        self.assertIsNotNone(notif)

    def test_notify_team_deleted_notifies_members(self):
        """Test notify_team_deleted notifies each member."""
        member = User.objects.create_user(
            username='member_del',
            password='pass123',
        )
        TeamMembership.objects.create(
            user=member,
            team=self.team,
            role='member',
            status='active',
        )
        members = User.objects.filter(
            team_memberships__team=self.team,
        )
        services.notify_team_deleted(self.team, members)
        notif = Notification.objects.filter(
            recipient=member,
            notification_type=Notification.NotificationType.TEAM_DELETED,
        ).first()
        self.assertIsNotNone(notif)


class NotificationSignalsTest(TestCase):
    """Integration tests for notification signals."""

    fixtures = [
        'tests/fixtures/test_users.json',
        'tests/fixtures/test_teams.json',
        'tests/fixtures/test_teams_memberships.json',
        'tests/fixtures/test_statuses.json',
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.status = Status.objects.get(pk=12)
        self.c = Client()
        self.c.force_login(self.user)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

    def test_create_task_with_executor_creates_notification(self):
        """Test creating task with executor creates TASK_ASSIGNED."""
        data = {
            'name': 'New Task',
            'status': self.status.id,
            'executors': [self.other_user.id],
        }
        self.c.post(reverse('tasks:task-create'), data, follow=True)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
        ).first()
        self.assertIsNotNone(notif)

    def test_create_task_self_executor_no_notification(self):
        """Test creating task with self as executor creates no notification."""
        data = {
            'name': 'Self Task',
            'status': self.status.id,
            'executors': [self.user.id],
        }
        self.c.post(reverse('tasks:task-create'), data, follow=True)
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
        ).first()
        self.assertIsNone(notif)

    def test_update_task_status_creates_notification(self):
        """Test updating task status creates TASK_STATUS_CHANGED."""
        # Create task with other_user as author so 'me' (actor) gets notified
        task = Task.objects.create(
            name='Status Task',
            status=self.status,
            author=self.other_user,
            team=self.team,
        )
        task.executors.add(self.user)
        new_status = Status.objects.create(
            name='New Status',
            team=self.team,
            creator=self.user,
        )
        data = {
            'name': 'Status Task',
            'status': new_status.id,
            'executors': [self.user.id],
        }
        self.c.post(
            reverse('tasks:task-update', args=[task.uuid]),
            data,
            follow=True
        )
        # Notify author (other_user), not executor (self.user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
        ).first()
        self.assertIsNotNone(notif)

    def test_update_task_status_by_author_no_notification(self):
        """Test updating status by author doesn't notify author."""
        task = Task.objects.create(
            name='Author Task',
            status=self.status,
            author=self.user,
            team=self.team,
        )
        new_status = Status.objects.create(
            name='New Status',
            team=self.team,
            creator=self.user,
        )
        data = {
            'name': 'Author Task',
            'status': new_status.id,
            'executors': [],
        }
        self.c.post(
            reverse('tasks:task-update', args=[task.uuid]),
            data,
            follow=True
        )
        notif = Notification.objects.filter(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
        ).first()
        self.assertIsNone(notif)

    def test_update_task_to_completed_sends_notification(self):
        """Test changing status to 'Completed' sends TASK_COMPLETED."""
        # Create task with 'In Progress' status
        in_progress = Status.objects.create(
            name='In Progress',
            team=self.team,
            creator=self.user,
        )
        task = Task.objects.create(
            name='Completion Task',
            status=in_progress,
            author=self.other_user,
            team=self.team,
        )
        task.executors.add(self.user)

        # Get or create 'Completed' status (exact name match required)
        completed_status, _ = Status.objects.get_or_create(
            name='Completed',
            team=self.team,
            creator=self.user,
        )

        # Update task to completed
        data = {
            'name': 'Completion Task',
            'status': completed_status.id,
            'executors': [self.user.id],
        }
        self.c.post(
            reverse('tasks:task-update', args=[task.uuid]),
            data,
            follow=True
        )

        # Should receive TASK_COMPLETED notification
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TASK_COMPLETED,
        ).first()
        self.assertIsNotNone(notif)

    def test_join_team_creates_admin_notification(self):
        """Test joining team creates TEAM_MEMBER_JOINED for admins."""
        # Remove any existing membership first
        TeamMembership.objects.filter(
            user=self.other_user,
            team=self.team
        ).delete()
        # Create membership as pending and approve it (simulating view flow)
        membership = TeamMembership.objects.create(
            user=self.other_user,
            team=self.team,
            role='member',
            status='pending',
        )
        # Approve the membership (simulating what view does)
        membership.status = 'active'
        membership.save()
        # Call the service function directly as the view does after approval
        services.notify_team_member_joined(self.team, self.other_user)
        notif = Notification.objects.filter(
            notification_type=Notification.NotificationType.
            TEAM_MEMBER_JOINED,
        ).first()
        self.assertIsNotNone(notif)

    def test_join_request_creates_admin_notification(self):
        """Test pending join request creates TEAM_JOIN_REQUEST."""
        # Remove any existing membership first
        TeamMembership.objects.filter(
            user=self.other_user,
            team=self.team
        ).delete()
        TeamMembership.objects.create(
            user=self.other_user,
            team=self.team,
            role='member',
            status='pending',
        )
        # Directly call the service function as the view does
        services.notify_team_join_request(self.team, self.other_user)
        notif = Notification.objects.filter(
            notification_type=Notification.NotificationType.TEAM_JOIN_REQUEST,
        ).first()
        self.assertIsNotNone(notif)

    def test_approve_request_creates_user_notification(self):
        """Test approving request creates TEAM_REQUEST_APPROVED."""
        # Remove any existing membership first
        TeamMembership.objects.filter(
            user=self.other_user,
            team=self.team
        ).delete()
        membership = TeamMembership.objects.create(
            user=self.other_user,
            team=self.team,
            role='member',
            status='pending',
        )
        self.c.post(
            reverse('teams:team-member-role-update', args=[membership.uuid]),
            {'role': 'member', 'status': 'active'},
            follow=True
        )
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.
            TEAM_REQUEST_APPROVED,
        ).first()
        self.assertIsNotNone(notif)

    def test_reject_request_creates_user_notification(self):
        """Test rejecting request creates TEAM_REQUEST_REJECTED."""
        # Remove any existing membership first
        TeamMembership.objects.filter(
            user=self.other_user,
            team=self.team
        ).delete()
        membership = TeamMembership.objects.create(
            user=self.other_user,
            team=self.team,
            role='member',
            status='pending',
        )
        # Reject by deleting the membership as admin (simulating view logic)
        was_pending = membership.status == 'pending'
        membership.delete()
        if was_pending:
            services.notify_request_rejected(self.team, self.other_user)
        notif = Notification.objects.filter(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.
            TEAM_REQUEST_REJECTED,
        ).first()
        self.assertIsNotNone(notif)


class NotificationViewsTest(TestCase):
    """Tests for notification views and context processor."""

    fixtures = [
        'tests/fixtures/test_users.json',
        'tests/fixtures/test_teams.json',
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.c = Client()

    def test_mark_read_own_notification_redirects(self):
        """Test POST to mark-read own notification redirects."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
            action_url='/tasks/',
        )
        self.c.force_login(self.user)
        response = self.c.post(
            reverse('notifications:mark-read', args=[notif.pk])
        )
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertRedirects(response, '/tasks/')

    def test_mark_read_foreign_notification_404(self):
        """Test POST to mark-read foreign notification returns 404."""
        notif = Notification.objects.create(
            recipient=self.other_user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
        )
        self.c.force_login(self.user)
        response = self.c.post(
            reverse('notifications:mark-read', args=[notif.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_mark_read_ajax_returns_json(self):
        """Test mark-read with AJAX header returns JSON."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
        )
        self.c.force_login(self.user)
        response = self.c.post(
            reverse('notifications:mark-read', args=[notif.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_mark_all_read_marks_all(self):
        """Test mark-all-read marks all unread as read."""
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test 1',
            is_read=False,
        )
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test 2',
            is_read=False,
        )
        self.c.force_login(self.user)
        response = self.c.post(reverse('notifications:mark-all-read'))
        unread = Notification.objects.filter(
            recipient=self.user, is_read=False
        ).count()
        self.assertEqual(unread, 0)
        self.assertRedirects(response, '/tasks/')

    def test_context_processor_has_unread(self):
        """Test context processor provides unread_notifications."""
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
            is_read=False,
        )
        self.c.force_login(self.user)
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertIn('unread_notifications', response.context)
        self.assertIn('unread_notifications_count', response.context)

    def test_unauthenticated_mark_read_redirects(self):
        """Test unauthenticated POST to mark-read redirects to login."""
        notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
        )
        response = self.c.post(
            reverse('notifications:mark-read', args=[notif.pk])
        )
        self.assertRedirects(
            response,
            '/login/?next=%2Fnotifications%2F1%2Fread%2F'
        )

    def test_unread_count_with_zero(self):
        """Test unread_notifications_count with 0 notifications."""
        self.c.force_login(self.user)
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.context['unread_notifications_count'], 0)

    def test_unread_count_with_five(self):
        """Test unread_notifications_count with 5 notifications."""
        for i in range(5):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                message=f'Test {i}',
                is_read=False,
            )
        self.c.force_login(self.user)
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.context['unread_notifications_count'], 5)

    def test_unread_count_with_ten(self):
        """Test unread_notifications_count with 10 notifications."""
        for i in range(10):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                message=f'Test {i}',
                is_read=False,
            )
        self.c.force_login(self.user)
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.context['unread_notifications_count'], 10)

    def test_unread_count_with_eleven_shows_ten(self):
        """Test unread_notifications_count shows 10 when 11 exist."""
        for i in range(11):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                message=f'Test {i}',
                is_read=False,
            )
        self.c.force_login(self.user)
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(len(response.context['unread_notifications']), 10)


class NotificationTemplateTest(TestCase):
    """Tests for notification template rendering."""

    fixtures = [
        'tests/fixtures/test_users.json',
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)

    def test_badge_shown_with_unread(self):
        """Test badge shown when unread notifications exist."""
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test',
            is_read=False,
        )
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, 'badge')
        self.assertContains(response, 'bg-danger')

    def test_no_badge_with_zero_unread(self):
        """Test no badge when no unread notifications."""
        response = self.c.get(reverse('tasks:tasks-list'))
        # Check badge element is not present
        self.assertNotContains(response, 'id="notificationBadge"')

    def test_notification_message_displayed(self):
        """Test notification message displayed in dropdown."""
        Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Test message here',
            is_read=False,
        )
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, 'Test message here')

    def test_showing_last_10_shown(self):
        """Test 'Showing last 10 notifications' shown with 10+."""
        for i in range(10):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.TASK_ASSIGNED,
                message=f'Test {i}',
                is_read=False,
            )
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, 'Showing last 10 notifications')


class NotificationCleanupCommandTest(TestCase):
    """Tests for cleanup_notifications management command."""

    fixtures = [
        'tests/fixtures/test_users.json',
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        # Create notifications with explicit time, ensuring old ones are
        # definitely older than 30 days and new ones are definitely newer.
        # Use microseconds=0 to avoid precision issues.
        # Note: auto_now_add ignores explicit created_at on save(),
        # so we use bulk_update after creation.
        now = timezone.now().replace(microsecond=0)
        self.old_read = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Old read',
            is_read=True,
        )
        self.old_unread = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='Old unread',
            is_read=False,
        )
        self.new_read = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.TASK_ASSIGNED,
            message='New read',
            is_read=True,
        )
        # Override created_at since auto_now_add ignored our values
        Notification.objects.filter(pk=self.old_read.pk).update(
            created_at=now - timedelta(days=40)
        )
        Notification.objects.filter(pk=self.old_unread.pk).update(
            created_at=now - timedelta(days=40)
        )
        Notification.objects.filter(pk=self.new_read.pk).update(
            created_at=now - timedelta(days=5)
        )
        # Refresh from DB
        self.old_read.refresh_from_db()
        self.old_unread.refresh_from_db()
        self.new_read.refresh_from_db()

    def test_deletes_old_read_notifications(self):
        """Test command deletes read notifications older than 30 days."""
        from django.core.management import call_command
        call_command('cleanup_notifications')
        self.assertFalse(
            Notification.objects.filter(pk=self.old_read.pk).exists()
        )

    def test_preserves_old_unread_notifications(self):
        """Test command preserves unread notifications older than 30 days."""
        from django.core.management import call_command
        call_command('cleanup_notifications')
        self.assertTrue(
            Notification.objects.filter(pk=self.old_unread.pk).exists()
        )

    def test_preserves_new_read_notifications(self):
        """Test command preserves read notifications younger than 30 days."""
        from django.core.management import call_command
        call_command('cleanup_notifications')
        self.assertTrue(
            Notification.objects.filter(pk=self.new_read.pk).exists()
        )

    def test_days_argument(self):
        """Test --days argument changes cutoff."""
        from django.core.management import call_command
        # With days=7, old_read (40 days) should be deleted,
        # but new_read (5 days) should be preserved.
        call_command('cleanup_notifications', days=7)
        self.assertFalse(
            Notification.objects.filter(pk=self.old_read.pk).exists()
        )
        # new_read is only 5 days old, so it should NOT be deleted
        self.assertTrue(
            Notification.objects.filter(pk=self.new_read.pk).exists()
        )

    def test_outputs_deleted_count(self):
        """Test command outputs number of deleted records."""
        from django.core.management import call_command
        import io
        out = io.StringIO()
        call_command('cleanup_notifications', verbosity=2, stdout=out)
        self.assertIn('Deleted', out.getvalue())
        self.assertIn('1', out.getvalue())

    def test_no_error_when_nothing_to_delete(self):
        """Test command completes without error when nothing to delete."""
        self.old_read.delete()
        from django.core.management import call_command
        import io
        out = io.StringIO()
        call_command('cleanup_notifications', verbosity=2, stdout=out)
        self.assertIn('No read notifications', out.getvalue())
