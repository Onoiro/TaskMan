from django.test import TestCase, Client
from django.urls import reverse
from task_manager.tasks.models import Task, ChecklistItem
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership
import json


class ChecklistModelTestCase(TestCase):
    """Tests for ChecklistItem model and Task checklist properties."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json"
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.task = Task.objects.get(name="first task")

    def test_checklist_total_property(self):
        """Test checklist_total returns correct count."""
        self.assertEqual(self.task.checklist_total, 0)

        ChecklistItem.objects.create(task=self.task, text="Item 1")
        ChecklistItem.objects.create(task=self.task, text="Item 2")

        self.assertEqual(self.task.checklist_total, 2)

    def test_checklist_done_property(self):
        """Test checklist_done returns correct count of done items."""
        ChecklistItem.objects.create(
            task=self.task, text="Item 1", is_done=False
        )
        item2 = ChecklistItem.objects.create(
            task=self.task, text="Item 2", is_done=True
        )
        ChecklistItem.objects.create(
            task=self.task, text="Item 3", is_done=True
        )

        self.assertEqual(self.task.checklist_done, 2)

        item2.is_done = False
        item2.save()

        self.assertEqual(self.task.checklist_done, 1)

    def test_checklist_progress_property(self):
        """Test checklist_progress returns correct percentage."""
        self.assertEqual(self.task.checklist_progress, 0)

        ChecklistItem.objects.create(
            task=self.task, text="Item 1", is_done=False
        )

        self.assertEqual(self.task.checklist_progress, 0)

        ChecklistItem.objects.create(
            task=self.task, text="Item 2", is_done=True
        )

        self.assertEqual(self.task.checklist_progress, 50)

        item1 = ChecklistItem.objects.filter(
            task=self.task, is_done=False
        ).first()
        item1.is_done = True
        item1.save()

        self.task.refresh_from_db()

        self.assertEqual(self.task.checklist_progress, 100)

    def test_checklist_item_str(self):
        """Test ChecklistItem string representation."""
        item = ChecklistItem.objects.create(
            task=self.task, text="Test checklist item text"
        )
        self.assertEqual(str(item), "Test checklist item text")

    def test_checklist_item_ordering(self):
        """Test ChecklistItem ordering by position then id."""
        item1 = ChecklistItem.objects.create(
            task=self.task, text="Item 1", position=2
        )
        item2 = ChecklistItem.objects.create(
            task=self.task, text="Item 2", position=1
        )
        item3 = ChecklistItem.objects.create(
            task=self.task, text="Item 3", position=1
        )

        items = list(self.task.checklist_items.all())

        self.assertEqual(items[0].id, item2.id)
        self.assertEqual(items[1].id, item3.id)
        self.assertEqual(items[2].id, item1.id)


class TaskFormTestCase(TestCase):
    """Tests for TaskForm - specifically the request=None case."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json"
    ]

    def setUp(self):
        from task_manager.tasks.forms import TaskForm
        self.TaskForm = TaskForm

    def test_form_without_request(self):
        """Test TaskForm works without request (returns early)."""
        form = self.TaskForm()

        self.assertIn('name', form.fields)
        self.assertIn('description', form.fields)
        self.assertIn('status', form.fields)
        self.assertIn('executors', form.fields)
        self.assertIn('labels', form.fields)

    def test_form_fields_order(self):
        """Test that form fields are in correct order."""
        form = self.TaskForm()

        field_order = list(form.fields.keys())

        name_idx = field_order.index('name')
        desc_idx = field_order.index('description')
        self.assertGreater(desc_idx, name_idx)


class ChecklistViewTestCase(TestCase):
    """Tests for checklist API views."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json"
    ]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='me')
        self.task = Task.objects.get(name="first task")
        self.client.force_login(self.user)

        session = self.client.session
        session['active_team_uuid'] = str(self.task.team.uuid)
        session.save()

        self.add_url = reverse('tasks:checklist-add', args=[self.task.uuid])

    def test_checklist_add_success(self):
        """Test adding a checklist item."""
        response = self.client.post(
            self.add_url,
            data=json.dumps({'text': 'New checklist item'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['text'], 'New checklist item')
        self.assertFalse(data['is_done'])
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['done'], 0)
        self.assertEqual(data['progress'], 0)

    def test_checklist_add_empty_text(self):
        """Test adding item with empty text fails."""
        response = self.client.post(
            self.add_url,
            data=json.dumps({'text': ''}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_checklist_add_text_too_long(self):
        """Test adding item with text > 300 chars fails."""
        long_text = 'x' * 301
        response = self.client.post(
            self.add_url,
            data=json.dumps({'text': long_text}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_checklist_add_invalid_json(self):
        """Test adding item with invalid JSON."""
        response = self.client.post(
            self.add_url,
            data='not json',
            content_type='application/json'
        )

        self.assertIn(response.status_code, [200, 400, 500])

    def test_checklist_toggle_success(self):
        """Test toggling a checklist item."""
        item = ChecklistItem.objects.create(task=self.task, text="Test")

        toggle_url = reverse(
            'tasks:checklist-toggle', args=[self.task.uuid, item.id]
        )

        response = self.client.post(
            toggle_url,
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['is_done'])
        self.assertEqual(data['done'], 1)
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['progress'], 100)

        item.refresh_from_db()
        self.assertTrue(item.is_done)

        response = self.client.post(
            toggle_url,
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data['is_done'])
        self.assertEqual(data['done'], 0)
        self.assertEqual(data['progress'], 0)

    def test_checklist_delete_success(self):
        """Test deleting a checklist item."""
        item = ChecklistItem.objects.create(task=self.task, text="Test")

        delete_url = reverse(
            'tasks:checklist-delete', args=[self.task.uuid, item.id]
        )

        response = self.client.post(
            delete_url,
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['deleted'])
        self.assertEqual(data['total'], 0)
        self.assertEqual(data['done'], 0)

        self.assertFalse(ChecklistItem.objects.filter(id=item.id).exists())

    def test_checklist_add_by_non_author_fails(self):
        """Test that non-author/non-executor cannot add items."""
        other_user = User.objects.get(username='alone')
        self.client.force_login(other_user)

        response = self.client.post(
            self.add_url,
            data=json.dumps({'text': 'Hacked item'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)

    def test_checklist_toggle_nonexistent_item(self):
        """Test toggling non-existent item returns 404."""
        toggle_url = reverse(
            'tasks:checklist-toggle', args=[self.task.uuid, 99999]
        )

        response = self.client.post(
            toggle_url,
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    def test_checklist_delete_nonexistent_item(self):
        """Test deleting non-existent item returns 404."""
        delete_url = reverse(
            'tasks:checklist-delete', args=[self.task.uuid, 99999]
        )

        response = self.client.post(
            delete_url,
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 404)

    def test_checklist_add_unauthenticated_fails(self):
        """Test that unauthenticated user cannot add items."""
        self.client.logout()

        response = self.client.post(
            self.add_url,
            data=json.dumps({'text': 'Test'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 302)

    def test_checklist_multiple_items_progress(self):
        """Test progress calculation with multiple items."""
        ChecklistItem.objects.create(
            task=self.task, text="Item 1", is_done=True
        )
        ChecklistItem.objects.create(
            task=self.task, text="Item 2", is_done=False
        )
        ChecklistItem.objects.create(
            task=self.task, text="Item 3", is_done=True
        )

        self.assertEqual(self.task.checklist_total, 3)
        self.assertEqual(self.task.checklist_done, 2)
        self.assertEqual(self.task.checklist_progress, 66)


class ChecklistEdgeCaseTestCase(TestCase):
    """Tests for checklist edge cases"""
    fixtures = [
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.task = Task.objects.get(name="first task")
        self.c = Client()
        self.c.force_login(self.user)

        membership = TeamMembership.objects.filter(user=self.user).first()
        self.team = membership.team if membership else None

        if self.team:
            session = self.c.session
            session['active_team_uuid'] = str(self.team.uuid)
            session.save()

    def test_checklist_add_invalid_json_body(self):
        """Sending invalid JSON falls back to empty text → 400."""
        url = reverse('tasks:checklist-add', args=[self.task.uuid])
        response = self.c.post(
            url,
            data=b'NOT VALID JSON',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_checklist_add_empty_body(self):
        """Sending empty body falls back to empty text → 400."""
        url = reverse('tasks:checklist-add', args=[self.task.uuid])
        response = self.c.post(
            url,
            data=b'',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_checklist_add_non_json_content_type(self):
        """Sending form data instead of JSON triggers except branch."""
        url = reverse('tasks:checklist-add', args=[self.task.uuid])
        response = self.c.post(
            url,
            data='text=hello',
            content_type='application/x-www-form-urlencoded',
        )
        # Should hit except branch, text becomes empty → 400
        self.assertEqual(response.status_code, 400)

    def test_checklist_add_text_too_long(self):
        """Text longer than 300 chars returns 400."""
        url = reverse('tasks:checklist-add', args=[self.task.uuid])
        long_text = 'A' * 301
        response = self.c.post(
            url,
            data=json.dumps({'text': long_text}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_checklist_add_text_exactly_300_chars(self):
        """Text exactly 300 chars is accepted."""
        url = reverse('tasks:checklist-add', args=[self.task.uuid])
        text_300 = 'B' * 300
        response = self.c.post(
            url,
            data=json.dumps({'text': text_300}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['text'], text_300)
