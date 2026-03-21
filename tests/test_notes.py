from task_manager.notes.models import Note
from task_manager.notes.forms import NoteForm
from task_manager.tasks.models import Task
from task_manager.user.models import User
from task_manager.teams.models import Team
from task_manager.statuses.models import Status
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages
import uuid as uuid_module


class NoteModelTestCase(TestCase):
    """Tests for Note model."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.status = Status.objects.get(pk=12)
        self.task = Task.objects.get(name="first task")

    def test_create_individual_note(self):
        """Test creating a personal note without team."""
        note = Note.objects.create(
            title="Personal Note",
            content="This is my personal note",
            author=self.user,
            team=None
        )
        self.assertEqual(note.title, "Personal Note")
        self.assertEqual(note.author, self.user)
        self.assertIsNone(note.team)
        self.assertIsNotNone(note.uuid)

    def test_create_team_note(self):
        """Test creating a team note."""
        note = Note.objects.create(
            title="Team Note",
            content="This is a team note",
            author=self.user,
            team=self.team
        )
        self.assertEqual(note.title, "Team Note")
        self.assertEqual(note.team, self.team)
        self.assertEqual(note.author, self.user)

    def test_create_note_with_task(self):
        """Test creating a note linked to a task."""
        note = Note.objects.create(
            title="Task Note",
            content="Note for task",
            author=self.user,
            team=self.team,
            task=self.task
        )
        self.assertEqual(note.task, self.task)
        self.assertIn(note, self.task.notes.all())

    def test_str_method_with_title(self):
        """Test __str__ returns title when set."""
        note = Note.objects.create(
            title="My Title",
            content="Content",
            author=self.user
        )
        self.assertEqual(str(note), "My Title")

    def test_str_method_without_title(self):
        """Test __str__ returns 'Note {id}' when no title."""
        note = Note.objects.create(
            title="",
            content="Content",
            author=self.user
        )
        self.assertEqual(str(note), f"Note {note.id}")

    def test_note_survives_task_deletion(self):
        """Test that note remains when task is deleted (task becomes None)."""
        note = Note.objects.create(
            title="Note for task",
            content="Content",
            author=self.user,
            team=self.team,
            task=self.task
        )
        self.task.delete()

        note.refresh_from_db()
        self.assertIsNotNone(Note.objects.filter(pk=note.pk).first())
        self.assertIsNone(note.task)

    def test_note_deleted_with_team(self):
        """Test that note is deleted when team is deleted (CASCADE)."""
        new_team = Team.objects.create(
            name="Team to delete",
            description="Will be deleted",
            password="test123"
        )
        note = Note.objects.create(
            title="Team note",
            content="Will be deleted with team",
            author=self.user,
            team=new_team
        )
        note_pk = note.pk

        new_team.delete()

        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_note_ordering_by_created_at_desc(self):
        """Test that notes are ordered by created_at descending."""
        note1 = Note.objects.create(
            title="First Note",
            content="Content 1",
            author=self.user
        )
        note2 = Note.objects.create(
            title="Second Note",
            content="Content 2",
            author=self.user
        )
        notes = list(Note.objects.filter(pk__in=[note1.pk, note2.pk]))
        # Most recent first
        self.assertEqual(notes[0], note2)
        self.assertEqual(notes[1], note1)


class NotePermissionsTestCase(TestCase):
    """Tests for Note permissions."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.author = User.objects.get(username='me')
        self.other_member = User.objects.get(username='he')
        self.outsider = User.objects.get(pk=13)
        self.team = Team.objects.get(pk=1)
        self.other_team = Team.objects.get(pk=2)
        self.status = Status.objects.get(pk=12)
        self.task = Task.objects.get(name="first task")

        self.c = Client()

    def test_author_can_update_own_note(self):
        """Test that author can edit their own note."""
        note = Note.objects.create(
            title="Author's Note",
            content="Original content",
            author=self.author,
            team=self.team
        )

        self.c.force_login(self.author)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Updated Title', 'content': 'Updated content'},
            follow=True
        )

        note.refresh_from_db()
        self.assertEqual(note.title, 'Updated Title')
        self.assertEqual(response.status_code, 200)

    def test_author_can_delete_own_note(self):
        """Test that author can delete their own note."""
        note = Note.objects.create(
            title="Note to delete",
            content="Content",
            author=self.author,
            team=self.team
        )

        self.c.force_login(self.author)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-delete', args=[note.uuid]),
            follow=True
        )

        self.assertFalse(Note.objects.filter(pk=note.pk).exists())
        self.assertEqual(response.status_code, 200)

    def test_non_author_member_cannot_update_team_note(self):
        """Test that non-author team member cannot edit another's note."""
        note = Note.objects.create(
            title="Team Note",
            content="Content",
            author=self.author,
            team=self.team
        )

        self.c.force_login(self.other_member)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Hacked Title', 'content': 'Hacked content'},
            follow=True
        )

        note.refresh_from_db()
        self.assertEqual(note.title, 'Team Note')

    def test_non_author_member_can_view_team_note(self):
        """Test that team member can view another member's team note."""
        note = Note.objects.create(
            title="Team Note",
            content="Shared content",
            author=self.author,
            team=self.team
        )

        self.c.force_login(self.other_member)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-detail', args=[note.uuid]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team Note")
        self.assertContains(response, "Shared content")

    def test_team_admin_can_delete_others_note(self):
        """Test that team admin can delete another member's note."""
        note = Note.objects.create(
            title="Member's Note",
            content="Content by member",
            author=self.other_member,
            team=self.team
        )

        self.c.force_login(self.author)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-delete', args=[note.uuid]),
            follow=True
        )

        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_team_admin_can_update_others_note(self):
        """Test that team admin can update another member's note."""
        note = Note.objects.create(
            title="Member's Note",
            content="Content by member",
            author=self.other_member,
            team=self.team
        )

        self.c.force_login(self.author)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Admin Updated', 'content': 'Changed by admin'},
            follow=True
        )

        note.refresh_from_db()
        self.assertEqual(note.title, 'Admin Updated')

    def test_user_cannot_see_other_team_notes(self):
        """Test that user cannot see notes from another team."""
        note = Note.objects.create(
            title="Team 1 Note",
            content="Secret content",
            author=self.author,
            team=self.team
        )

        self.c.force_login(self.outsider)

        response = self.c.get(reverse('notes:note-list'))
        self.assertNotContains(response, "Team 1 Note")

        response = self.c.get(reverse('notes:note-detail', args=[note.uuid]))
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_access_individual_note_of_others(self):
        """Test that user cannot access another user's individual notes."""
        note = Note.objects.create(
            title="Private Note",
            content="Private content",
            author=self.author,
            team=None
        )

        self.c.force_login(self.other_member)

        response = self.c.get(reverse('notes:note-detail', args=[note.uuid]))
        self.assertEqual(response.status_code, 404)


class NoteViewsTestCase(TestCase):
    """Tests for Note views."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.status = Status.objects.get(pk=12)
        self.task = Task.objects.get(name="first task")

        self.c = Client()
        self.c.force_login(self.user)

    def test_note_list_returns_only_context_notes(self):
        """Test that note list returns only notes for current context."""
        Note.objects.create(
            title="Team Note",
            content="Team content",
            author=self.user,
            team=self.team
        )
        Note.objects.create(
            title="Individual Note",
            content="Individual content",
            author=self.user,
            team=None
        )
        other_team = Team.objects.get(pk=2)
        Note.objects.create(
            title="Other Team Note",
            content="Other team content",
            author=self.user,
            team=other_team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-list'))
        self.assertContains(response, "Team Note")
        self.assertNotContains(response, "Individual Note")
        self.assertNotContains(response, "Other Team Note")

        session['active_team_uuid'] = None
        session.save()

        response = self.c.get(reverse('notes:note-list'))
        self.assertContains(response, "Individual Note")
        self.assertNotContains(response, "Team Note")

    def test_create_note_without_team_creates_individual(self):
        """Test that creating note without active team creates individual."""
        self.c.post(
            reverse('notes:note-create'),
            {'title': 'Personal Note', 'content': 'My content'},
            follow=True
        )

        note = Note.objects.get(title='Personal Note')
        self.assertIsNone(note.team)
        self.assertEqual(note.author, self.user)

    def test_create_note_with_team_context_sets_team_automatically(self):
        """Test that creating note in team context sets team automatically."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-create'),
            {'title': 'Team Note', 'content': 'Team content'},
            follow=True
        )

        note = Note.objects.get(title='Team Note')
        self.assertEqual(note.team, self.team)
        self.assertEqual(note.author, self.user)

    def test_update_foreign_note_returns_forbidden(self):
        """Test that updating another's note is forbidden for non-admin."""
        note = Note.objects.create(
            title="Other's Note",
            content="Content",
            author=self.other_user,
            team=self.team
        )

        outsider = User.objects.get(pk=13)
        self.c.force_login(outsider)

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Hacked', 'content': 'Hacked'},
            follow=True
        )

        note.refresh_from_db()
        self.assertEqual(note.title, "Other's Note")

    def test_note_list_filter_by_task(self):
        """Test filtering notes by task."""
        other_task = Task.objects.create(
            name="Other Task",
            status=self.status,
            author=self.user,
            team=self.team
        )

        Note.objects.create(
            title="Note for Task 1",
            content="Content",
            author=self.user,
            team=self.team,
            task=self.task
        )
        Note.objects.create(
            title="Note for Other Task",
            content="Content",
            author=self.user,
            team=self.team,
            task=other_task
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(
            reverse('notes:note-list') + f'?task={self.task.uuid}'
        )

        self.assertContains(response, "Note for Task 1")
        self.assertNotContains(response, "Note for Other Task")

    def test_note_create_with_task_parameter(self):
        """Test creating note with task parameter in URL."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-create') + f'?task={self.task.uuid}',
            {'title': 'Task Note', 'content': 'For task', 'task': self.task.id},
            follow=True
        )

        note = Note.objects.get(title='Task Note')
        self.assertEqual(note.task, self.task)

    def test_note_create_redirects_to_task_after_creation(self):
        """Test redirect to task page after creating note with task param."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-create') + f'?task={self.task.uuid}',
            {'title': 'Task Note', 'content': 'For task', 'task': self.task.id},
            follow=False
        )

        expected_url = reverse('tasks:task-update', args=[self.task.uuid])
        self.assertRedirects(response, expected_url)

    def test_note_update_redirects_to_task_if_linked(self):
        """Test redirect to task page after updating note linked to task."""
        note = Note.objects.create(
            title="Task Note",
            content="Content",
            author=self.user,
            team=self.team,
            task=self.task
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Updated', 'content': 'Updated', 'task': self.task.id},
            follow=False
        )

        expected_url = reverse('tasks:task-update', args=[self.task.uuid])
        self.assertRedirects(response, expected_url)

    def test_note_list_page_content(self):
        """Test note list page contains expected elements."""
        Note.objects.create(
            title="Test Note",
            content="Test content",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Note")

    def test_note_detail_page_content(self):
        """Test note detail page contains expected elements."""
        note = Note.objects.create(
            title="Detail Note",
            content="Detail content here",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-detail', args=[note.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Note")
        self.assertContains(response, "Detail content here")

    def test_note_create_page_content(self):
        """Test note create page contains expected elements."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Title'))
        self.assertContains(response, _('Content'))

    def test_note_update_page_content(self):
        """Test note update page contains expected elements."""
        note = Note.objects.create(
            title="Update Note",
            content="Content",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-update', args=[note.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update Note")

    def test_note_delete_page_content(self):
        """Test note delete confirmation page."""
        note = Note.objects.create(
            title="Delete Note",
            content="Content",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-delete', args=[note.uuid]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Delete'))

    def test_create_note_success_message(self):
        """Test success message after creating note."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-create'),
            {'title': 'New Note', 'content': 'Content'},
            follow=True
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Note created successfully'))

    def test_update_note_success_message(self):
        """Test success message after updating note."""
        note = Note.objects.create(
            title="Note",
            content="Content",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Updated', 'content': 'Updated'},
            follow=True
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Note updated successfully'))

    def test_delete_note_success_message(self):
        """Test success message after deleting note."""
        note = Note.objects.create(
            title="Note to delete",
            content="Content",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-delete', args=[note.uuid]),
            follow=True
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Note deleted successfully'))


class NoteIntegrationTestCase(TestCase):
    """Integration tests for Notes with Tasks."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.other_team = Team.objects.get(pk=2)
        self.status = Status.objects.get(pk=12)
        self.task = Task.objects.get(name="first task")

        self.c = Client()
        self.c.force_login(self.user)

    def test_task_notes_displayed_on_task_page(self):
        """Test that notes are displayed on task update page."""
        Note.objects.create(
            title="Note 1",
            content="Content 1",
            author=self.user,
            team=self.team,
            task=self.task
        )
        Note.objects.create(
            title="Note 2",
            content="Content 2",
            author=self.user,
            team=self.team,
            task=self.task
        )
        other_task = Task.objects.create(
            name="Other Task",
            status=self.status,
            author=self.user,
            team=self.team
        )
        Note.objects.create(
            title="Other Note",
            content="Other content",
            author=self.user,
            team=self.team,
            task=other_task
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.uuid])
        )

        self.assertContains(response, "Note 1")
        self.assertContains(response, "Note 2")
        self.assertNotContains(response, "Other Note")

    def test_cannot_attach_note_to_other_team_task(self):
        """Test that user cannot attach note to task from another team."""
        other_team_task = Task.objects.create(
            name="Other Team Task",
            status=self.status,
            author=self.user,
            team=self.other_team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        self.c.post(
            reverse('notes:note-create'),
            {'title': 'Note', 'content': 'Content', 'task': other_team_task.id},
            follow=True
        )

        note = Note.objects.filter(title='Note').first()
        if note:
            self.assertNotEqual(note.task, other_team_task)

    def test_cannot_attach_note_to_other_user_task_in_individual_mode(self):
        """Test cannot attach note to another user's task in individual mode."""
        other_user_task = Task.objects.create(
            name="Other User Task",
            status=self.status,
            author=self.other_user,
            team=None
        )

        self.c.post(
            reverse('notes:note-create'),
            {'title': 'Note', 'content': 'Content', 'task': other_user_task.id},
            follow=True
        )

        note = Note.objects.filter(title='Note').first()
        if note:
            self.assertNotEqual(note.task, other_user_task)

    def test_note_form_filters_tasks_by_context(self):
        """Test that note form only shows tasks from current context."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-create'))
        self.assertContains(response, 'task')

        session['active_team_uuid'] = None
        session.save()

        response = self.c.get(reverse('notes:note-create'))
        self.assertEqual(response.status_code, 200)

    def test_multiple_notes_for_same_task(self):
        """Test that multiple notes can be created for the same task."""
        note1 = Note.objects.create(
            title="First Note",
            content="Content 1",
            author=self.user,
            team=self.team,
            task=self.task
        )
        note2 = Note.objects.create(
            title="Second Note",
            content="Content 2",
            author=self.user,
            team=self.team,
            task=self.task
        )

        task_notes = self.task.notes.all()
        self.assertEqual(task_notes.count(), 2)
        self.assertIn(note1, task_notes)
        self.assertIn(note2, task_notes)

    def test_note_without_task_still_visible_in_list(self):
        """Test that notes without task are visible in note list."""
        Note.objects.create(
            title="Standalone Note",
            content="No task linked",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.get(reverse('notes:note-list'))
        self.assertContains(response, "Standalone Note")


class NoteFormTestCase(TestCase):
    """Tests for NoteForm validation."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.other_team = Team.objects.get(pk=2)
        self.status = Status.objects.get(pk=12)
        self.task = Task.objects.get(name="first task")
        self.factory = RequestFactory()

    def test_form_without_request(self):
        """Test that form works without request parameter."""
        form = NoteForm()
        self.assertIn('title', form.fields)
        self.assertIn('content', form.fields)
        self.assertIn('task', form.fields)

    def test_clean_task_team_context_wrong_team(self):
        """Test validation error when task from different team in team mode."""
        other_team_task = Task.objects.create(
            name="Other Team Task",
            status=self.status,
            author=self.user,
            team=self.other_team
        )

        request = self.factory.get('/')
        request.user = self.user
        request.active_team = self.team

        form = NoteForm(request=request)
        form.cleaned_data = {'task': other_team_task}

        with self.assertRaises(Exception) as context:
            form.clean_task()

        self.assertIn('same team', str(context.exception))

    def test_clean_task_individual_context_team_task(self):
        """Test validation error when team task in individual mode."""
        team_task = Task.objects.create(
            name="Team Task",
            status=self.status,
            author=self.user,
            team=self.team
        )

        request = self.factory.get('/')
        request.user = self.user
        request.active_team = None

        form = NoteForm(request=request)
        form.cleaned_data = {'task': team_task}

        with self.assertRaises(Exception) as context:
            form.clean_task()

        self.assertIn('individual mode', str(context.exception))

    def test_clean_task_individual_context_other_user_task(self):
        """Test validation error when other user's task in individual mode."""
        other_user_task = Task.objects.create(
            name="Other User Task",
            status=self.status,
            author=self.other_user,
            team=None
        )

        request = self.factory.get('/')
        request.user = self.user
        request.active_team = None

        form = NoteForm(request=request)
        form.cleaned_data = {'task': other_user_task}

        with self.assertRaises(Exception) as context:
            form.clean_task()

        self.assertIn('own tasks', str(context.exception))

    def test_clean_task_returns_task_when_valid(self):
        """Test that clean_task returns task when valid."""
        request = self.factory.get('/')
        request.user = self.user
        request.active_team = self.team

        form = NoteForm(request=request)
        form.cleaned_data = {'task': self.task}

        result = form.clean_task()
        self.assertEqual(result, self.task)

    def test_clean_task_returns_none_when_no_task(self):
        """Test that clean_task returns None when no task."""
        request = self.factory.get('/')
        request.user = self.user
        request.active_team = self.team

        form = NoteForm(request=request)
        form.cleaned_data = {'task': None}

        result = form.clean_task()
        self.assertIsNone(result)


class NoteViewsEdgeCasesTestCase(TestCase):
    """Tests for edge cases in Note views."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.other_user = User.objects.get(username='he')
        self.team = Team.objects.get(pk=1)
        self.status = Status.objects.get(pk=12)
        self.task = Task.objects.get(name="first task")

        self.c = Client()
        self.c.force_login(self.user)

    def test_create_note_with_nonexistent_task_uuid(self):
        """Test that non-existent task UUID is handled gracefully."""
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        fake_uuid = uuid_module.uuid4()
        response = self.c.get(
            reverse('notes:note-create') + f'?task={fake_uuid}'
        )
        self.assertEqual(response.status_code, 200)

    def test_non_admin_member_cannot_delete_others_note(self):
        """Test that non-admin team member cannot delete another's note."""
        note = Note.objects.create(
            title="Author's Note",
            content="Content",
            author=self.user,
            team=self.team
        )

        # other_user is a member but not admin
        self.c.force_login(self.other_user)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-delete', args=[note.uuid]),
            follow=True
        )

        # Note should still exist
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())
        # Should redirect to note list
        self.assertRedirects(response, reverse('notes:note-list'))

    def test_non_admin_member_cannot_update_others_note(self):
        """Test that non-admin team member cannot update another's note."""
        note = Note.objects.create(
            title="Author's Note",
            content="Content",
            author=self.user,
            team=self.team
        )

        # other_user is a member but not admin
        self.c.force_login(self.other_user)
        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-update', args=[note.uuid]),
            {'title': 'Hacked', 'content': 'Hacked'},
            follow=True
        )

        note.refresh_from_db()
        self.assertEqual(note.title, "Author's Note")
        self.assertRedirects(response, reverse('notes:note-list'))

    def test_delete_note_redirects_to_task_page(self):
        """Test that deleting note with task param redirects to task."""
        note = Note.objects.create(
            title="Note to delete",
            content="Content",
            author=self.user,
            team=self.team,
            task=self.task
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-delete', args=[note.uuid])
            + f'?task={self.task.uuid}',
            follow=False
        )

        expected_url = reverse('tasks:task-update', args=[self.task.uuid])
        self.assertRedirects(response, expected_url)

    def test_delete_note_redirects_to_list_without_task_param(self):
        """Test that deleting note without task param redirects to list."""
        note = Note.objects.create(
            title="Note to delete",
            content="Content",
            author=self.user,
            team=self.team
        )

        session = self.c.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.c.post(
            reverse('notes:note-delete', args=[note.uuid]),
            follow=False
        )

        self.assertRedirects(response, reverse('notes:note-list'))

    def test_delete_individual_note_in_individual_mode(self):
        """Test deleting individual note without active team."""
        note = Note.objects.create(
            title="Individual Note",
            content="Content",
            author=self.user,
            team=None
        )

        # No active team in session
        session = self.c.session
        session['active_team_uuid'] = None
        session.save()

        response = self.c.post(
            reverse('notes:note-delete', args=[note.uuid]),
            follow=False
        )

        self.assertFalse(Note.objects.filter(pk=note.pk).exists())
        self.assertRedirects(response, reverse('notes:note-list'))
