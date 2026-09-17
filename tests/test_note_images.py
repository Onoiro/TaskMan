import os
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from task_manager.notes.models import Note, NoteImage
from task_manager.user.models import User
from task_manager.teams.models import Team


def make_image_file(name='test.png', content=None, ext='.png'):
    """Create a minimal valid PNG file for uploads."""
    if content is None:
        # 1x1 transparent PNG
        content = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
    return SimpleUploadedFile(name, content, content_type='image/png')


def make_text_file(name='test.txt'):
    """Create a plain text file pretending to be an image."""
    return SimpleUploadedFile(
        name, b'not an image at all', content_type='image/png'
    )


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class NoteImageTestCase(TestCase):
    """Tests for note image upload, serving, deletion and cleanup."""

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
            title="With images",
            content="Content",
            author=self.user,
            team=None
        )
        self.client.force_login(self.user)

    def tearDown(self):
        # Remove leftover uploaded files
        for image in NoteImage.objects.all():
            if image.image:
                path = image.image.path
                image.image.delete(save=False)
                if os.path.exists(path):
                    os.remove(path)

    def _upload_url(self):
        return reverse('notes:note-update', kwargs={'uuid': self.note.uuid})

    def _detail_url(self):
        return reverse('notes:note-detail', kwargs={'uuid': self.note.uuid})

    # --- Upload ---

    def test_upload_image_to_note(self):
        """Author can attach an image via note update form."""
        response = self.client.post(
            self._upload_url(),
            {
                'title': 'With images',
                'content': 'Content',
                'images': [make_image_file('photo.png')],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 1)
        image = self.note.images.first()
        self.assertTrue(image.image)
        self.assertTrue(os.path.exists(image.image.path))

    def test_upload_multiple_images(self):
        """Multiple files are attached in one request."""
        files = [
            make_image_file('a.png'),
            make_image_file('b.png'),
        ]
        self.client.post(
            self._upload_url(),
            {'title': '', 'content': 'Content', 'images': files},
        )
        self.assertEqual(self.note.images.count(), 2)
        self.assertEqual(
            list(self.note.images.values_list('order', flat=True)),
            [0, 1]
        )

    def test_upload_rejects_oversized_image(self):
        """Files above the size limit are rejected with a message."""
        big = make_image_file(
            'big.png', content=b'x' * (NoteImage.MAX_IMAGE_SIZE_MB
                                       * 1024 * 1024 + 1)
        )
        response = self.client.post(
            self._upload_url(),
            {'title': '', 'content': 'Content', 'images': [big]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 0)

    def test_upload_rejects_text_file(self):
        """Non-image content is rejected by Pillow validation."""
        response = self.client.post(
            self._upload_url(),
            {'title': '', 'content': 'Content',
             'images': [make_text_file('fake.png')]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 0)

    def test_upload_rejects_wrong_extension(self):
        """Unsupported extensions are rejected."""
        response = self.client.post(
            self._upload_url(),
            {'title': '', 'content': 'Content',
             'images': [make_image_file('photo.bmp')]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 0)

    def test_upload_limit_ten_images(self):
        """No more than max_note_images images can be attached."""
        for i in range(10):
            NoteImage.objects.create(
                note=self.note,
                image=make_image_file(f'{i}.png'),
                order=i
            )
        response = self.client.post(
            self._upload_url(),
            {'title': '', 'content': 'Content',
             'images': [make_image_file('extra.png')]},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 10)

    # --- Private serving ---

    def test_author_can_view_image(self):
        """Author can fetch the image through the private view."""
        image = NoteImage.objects.create(
            note=self.note, image=make_image_file('photo.png'), order=0
        )
        url = reverse(
            'notes:note-image-detail',
            kwargs={'uuid': self.note.uuid, 'pk': image.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_view_image(self):
        """A stranger gets 404 for someone else's personal note image."""
        image = NoteImage.objects.create(
            note=self.note, image=make_image_file('photo.png'), order=0
        )
        self.client.force_login(self.other_user)
        url = reverse(
            'notes:note-image-detail',
            kwargs={'uuid': self.note.uuid, 'pk': image.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_cannot_view_image(self):
        """Anonymous users are redirected to login."""
        image = NoteImage.objects.create(
            note=self.note, image=make_image_file('photo.png'), order=0
        )
        self.client.logout()
        url = reverse(
            'notes:note-image-detail',
            kwargs={'uuid': self.note.uuid, 'pk': image.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    # --- Deletion and cleanup ---

    def test_delete_image_removes_file(self):
        """Deleting an image record also removes the file from disk."""
        image = NoteImage.objects.create(
            note=self.note, image=make_image_file('photo.png'), order=0
        )
        path = image.image.path
        self.assertTrue(os.path.exists(path))
        url = reverse('notes:note-image-delete', kwargs={'pk': image.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 0)
        self.assertFalse(os.path.exists(path))

    def test_other_user_cannot_delete_image(self):
        """Only author, team admin or superuser can delete images."""
        image = NoteImage.objects.create(
            note=self.note, image=make_image_file('photo.png'), order=0
        )
        self.client.force_login(self.other_user)
        url = reverse('notes:note-image-delete', kwargs={'pk': image.pk})
        response = self.client.post(url)
        # Redirected to note list with an error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.note.images.count(), 1)

    def test_deleting_note_removes_all_image_files(self):
        """CASCADE note deletion cleans up files from storage."""
        paths = []
        for i in range(3):
            image = NoteImage.objects.create(
                note=self.note, image=make_image_file(f'{i}.png'), order=i
            )
            paths.append(image.image.path)
        url = reverse('notes:note-delete', kwargs={'uuid': self.note.uuid})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(NoteImage.objects.count(), 0)
        for path in paths:
            self.assertFalse(os.path.exists(path))

    def test_detail_page_shows_gallery(self):
        """Note detail renders gallery thumbnails."""
        NoteImage.objects.create(
            note=self.note, image=make_image_file('photo.png'), order=0
        )
        response = self.client.get(self._detail_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'note-gallery-thumb')

    def test_team_member_can_view_team_note_image(self):
        """Team members can view images of their team's note."""
        team_note = Note.objects.create(
            title="Team note",
            content="Content",
            author=self.user,
            team=self.team
        )
        image = NoteImage.objects.create(
            note=team_note, image=make_image_file('photo.png'), order=0
        )
        # other_user is an active member of the team per fixtures
        self.client.force_login(self.other_user)
        session = self.client.session
        session['active_team_uuid'] = str(self.team.uuid)
        session.save()
        url = reverse(
            'notes:note-image-detail',
            kwargs={'uuid': team_note.uuid, 'pk': image.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
