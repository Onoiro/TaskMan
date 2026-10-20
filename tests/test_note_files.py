import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from task_manager.notes.models import Note, NoteFile
from task_manager.user.models import User
from task_manager.teams.models import Team


PDF_HEADER = b'%PDF-1.4 fake pdf content for tests'


def make_file(name='report.pdf', content=None):
    """Create a small upload with the given name."""
    if content is None:
        content = PDF_HEADER
    return SimpleUploadedFile(name, content)


def attach_file(note, name='report.pdf', content=None, order=0):
    """Create a NoteFile row keeping original_name in sync with the name."""
    return NoteFile.objects.create(
        note=note,
        file=make_file(name, content),
        original_name=name,
        order=order
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoteFileUploadTestCase(TestCase):
    """Tests for uploading file attachments to a note."""

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
        self.note = Note.objects.create(
            title="With files",
            content="Content",
            author=self.user,
            team=None
        )
        self.client.force_login(self.user)

    def _upload_url(self):
        return reverse('notes:note-update', kwargs={'uuid': self.note.uuid})

    def _post(self, files):
        return self.client.post(
            self._upload_url(),
            {'title': self.note.title, 'content': 'Content',
             'attachments': files},
        )

    # --- Upload ---

    def test_upload_file_to_note(self):
        """Author can attach a file via note update form."""
        response = self._post([make_file('report.pdf')])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.files.count(), 1)
        fobj = self.note.files.first()
        self.assertTrue(os.path.exists(fobj.file.path))

    def test_upload_multiple_files(self):
        """Multiple files are attached in one request."""
        self._post([make_file('a.pdf'), make_file('b.docx')])
        self.assertEqual(self.note.files.count(), 2)
        self.assertEqual(
            list(self.note.files.values_list('order', flat=True)),
            [0, 1]
        )

    def test_original_name_preserved(self):
        """The uploaded name is stored for display, not the hashed path."""
        self._post([make_file('My Report 2026.pdf')])
        fobj = self.note.files.first()
        self.assertEqual(fobj.original_name, 'My Report 2026.pdf')

    def test_upload_allows_pdf(self):
        """Documents from the whitelist are accepted."""
        self._post([make_file('doc.pdf')])
        self.assertEqual(self.note.files.count(), 1)

    def test_upload_allows_docx_and_zip(self):
        """Office documents and archives are accepted."""
        self._post([make_file('doc.docx'), make_file('archive.zip')])
        self.assertEqual(self.note.files.count(), 2)

    def test_upload_rejects_oversized_file(self):
        """Files above the size limit are rejected."""
        big = make_file(
            'big.pdf',
            content=b'x' * (NoteFile.MAX_FILE_SIZE_MB * 1024 * 1024 + 1)
        )
        response = self._post([big])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.files.count(), 0)

    def test_upload_rejects_blocked_extension(self):
        """Executables are rejected."""
        self._post([make_file('malware.exe')])
        self.assertEqual(self.note.files.count(), 0)

    def test_upload_rejects_svg(self):
        """Web formats are rejected even though they look like images."""
        self._post([make_file('icon.svg')])
        self.assertEqual(self.note.files.count(), 0)

    def test_upload_limit_ten_files(self):
        """No more than max_note_files files can be attached."""
        for i in range(10):
            attach_file(self.note, f'{i}.pdf', order=i)
        self._post([make_file('extra.pdf')])
        self.assertEqual(self.note.files.count(), 10)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoteFileServingTestCase(TestCase):
    """Tests for private download of note file attachments."""

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
        self.note = Note.objects.create(
            title="With files",
            content="Content",
            author=self.user,
            team=None
        )
        self.client.force_login(self.user)

    def _download_url(self, note, fobj):
        return reverse(
            'notes:note-file-download',
            kwargs={'uuid': note.uuid, 'pk': fobj.pk}
        )

    def test_file_download_private(self):
        """Author downloads the file, a stranger gets 404."""
        fobj = attach_file(self.note)
        response = self.client.get(self._download_url(self.note, fobj))
        self.assertEqual(response.status_code, 200)

        self.client.force_login(self.other_user)
        response = self.client.get(self._download_url(self.note, fobj))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_cannot_download_file(self):
        """Anonymous users are redirected to login."""
        fobj = attach_file(self.note)
        self.client.logout()
        response = self.client.get(self._download_url(self.note, fobj))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_file_download_content_disposition(self):
        """Files are always served as a download, never inline."""
        fobj = attach_file(self.note, 'report.pdf')
        response = self.client.get(self._download_url(self.note, fobj))
        disposition = response.get('Content-Disposition', '')
        self.assertIn('attachment', disposition)
        self.assertIn('report.pdf', disposition)

    def test_download_sets_nosniff_and_mime(self):
        """Response does not let the browser guess the content type."""
        fobj = attach_file(self.note, 'report.pdf')
        response = self.client.get(self._download_url(self.note, fobj))
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_team_member_can_download_team_note_file(self):
        """Team members can download files of their team's note."""
        team_note = Note.objects.create(
            title="Team note",
            content="Content",
            author=self.user,
            team=self.team
        )
        fobj = attach_file(team_note, 'team.pdf')

        self.client.force_login(self.other_user)
        session = self.client.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()

        response = self.client.get(self._download_url(team_note, fobj))
        self.assertEqual(response.status_code, 200)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoteFileDeleteTestCase(TestCase):
    """Tests for removing file attachments and storage cleanup."""

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
        self.note = Note.objects.create(
            title="With files",
            content="Content",
            author=self.user,
            team=None
        )
        self.client.force_login(self.user)

    def test_file_delete_removes_file(self):
        """Deleting a file record also removes the file from disk."""
        fobj = attach_file(self.note)
        path = fobj.file.path
        self.assertTrue(os.path.exists(path))

        response = self.client.post(
            reverse('notes:note-file-delete', kwargs={'pk': fobj.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.files.count(), 0)
        self.assertFalse(os.path.exists(path))

    def test_other_user_cannot_delete_file(self):
        """Only author, team admin or superuser can delete files."""
        fobj = attach_file(self.note)
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse('notes:note-file-delete', kwargs={'pk': fobj.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.files.count(), 1)

    def test_deleting_note_removes_all_files(self):
        """CASCADE note deletion cleans up files from storage."""
        paths = [
            attach_file(self.note, f'{i}.pdf', order=i).file.path
            for i in range(3)
        ]

        response = self.client.post(
            reverse('notes:note-delete', kwargs={'uuid': self.note.uuid})
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(NoteFile.objects.count(), 0)
        for path in paths:
            self.assertFalse(os.path.exists(path))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoteFileTemplatesTestCase(TestCase):
    """Tests for attachment sections in note templates."""

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
        self.note = Note.objects.create(
            title="With files",
            content="Content",
            author=self.user,
            team=None
        )
        self.client.force_login(self.user)

    def test_detail_page_shows_attachments(self):
        """Note detail renders the attachments section with download link."""
        fobj = attach_file(self.note, 'report.pdf')
        response = self.client.get(
            reverse('notes:note-detail', kwargs={'uuid': self.note.uuid})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'report.pdf')
        self.assertContains(
            response,
            reverse('notes:note-file-download',
                    kwargs={'uuid': self.note.uuid, 'pk': fobj.pk})
        )

    def test_detail_page_hides_attachments_without_files(self):
        """A note without attachments has no empty section."""
        response = self.client.get(
            reverse('notes:note-detail', kwargs={'uuid': self.note.uuid})
        )
        self.assertNotContains(response, 'note-files')

    def test_list_shows_paperclip_icon(self):
        """Note list marks notes that have attachments."""
        attach_file(self.note)
        response = self.client.get(reverse('notes:note-list'))
        self.assertContains(response, 'bi-paperclip')

    def test_list_hides_paperclip_without_files(self):
        """Notes without attachments show no paperclip."""
        response = self.client.get(reverse('notes:note-list'))
        self.assertNotContains(response, 'bi-paperclip')

    def test_form_has_attachments_input(self):
        """Edit form offers the attachments input."""
        response = self.client.get(
            reverse('notes:note-update', kwargs={'uuid': self.note.uuid})
        )
        self.assertContains(response, 'name="attachments"')
        self.assertContains(response, 'multiple')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoteFileFormTestCase(TestCase):
    """Attachments alone are enough to save a note without text."""

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
        self.client.force_login(self.user)

    def test_create_textless_note_with_file(self):
        """A note can be created with a file and no text."""
        response = self.client.post(
            reverse('notes:note-create'),
            {'content': '', 'attachments': [make_file('scan.pdf')]},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        note = Note.objects.get(author=self.user)
        self.assertEqual(note.content, '')
        self.assertEqual(note.files.count(), 1)

    def test_create_note_without_text_and_files_is_rejected(self):
        """Empty note is rejected and the message mentions files too."""
        response = self.client.post(
            reverse('notes:note-create'),
            {'content': ''},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Note.objects.exists())
        self.assertContains(response, 'attachments')

    def test_textless_note_kept_when_files_exist(self):
        """Existing attachments keep a note valid when its text is removed."""
        note = Note.objects.create(
            title='Note', content='Content', author=self.user, team=None
        )
        attach_file(note)

        response = self.client.post(
            reverse('notes:note-update', kwargs={'uuid': note.uuid}),
            {'title': 'Note', 'content': ''},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertEqual(note.content, '')
