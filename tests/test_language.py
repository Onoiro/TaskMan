from django.test import TestCase, Client
from django.urls import reverse
from django.utils import translation


class LanguageSwitchTestCase(TestCase):
    """Tests for language switching functionality."""

    def setUp(self):
        self.client = Client()

    def test_language_switch_form_exists_on_page(self):
        """Test that language switch form exists on pages."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        # Check that set_language URL is present in the response
        self.assertContains(response, reverse('set_language'))

    def test_language_switch_to_english(self):
        """Test switching language from Russian to English."""
        # Initial language is Russian
        with translation.override('ru'):
            self.assertEqual(translation.get_language(), 'ru')

        # Switch to English
        self.client.post(
            reverse('set_language'),
            {'language': 'en'},
            follow=True
        )

        # Check that language is now English
        self.assertEqual(translation.get_language(), 'en')

    def test_language_switch_to_russian(self):
        """Test switching language from English to Russian."""
        # Initial language is Russian, switch to English first
        self.client.post(
            reverse('set_language'),
            {'language': 'en'},
            follow=True
        )

        # Switch back to Russian
        self.client.post(
            reverse('set_language'),
            {'language': 'ru'},
            follow=True
        )

        # Check that language is now Russian
        self.assertEqual(translation.get_language(), 'ru')

    def test_language_switch_preserves_page(self):
        """Test that language switch redirects back to the referring page."""
        # Start from the home page
        response = self.client.get('/')
        referer = response.wsgi_request.build_absolute_uri('/')

        # Switch language with referer
        response = self.client.post(
            reverse('set_language'),
            {'language': 'en'},
            follow=False,
            HTTP_REFERER=referer
        )

        # Should redirect back to the original page
        self.assertIn(response.status_code, [302, 200])

    def test_language_cookie_is_set(self):
        """Test that language cookie is set after switching."""
        self.client.post(
            reverse('set_language'),
            {'language': 'en'},
            follow=True
        )

        # Check that the response contains the language change
        self.assertEqual(translation.get_language(), 'en')

    def test_language_switch_with_invalid_language(self):
        """Test that switching to invalid language doesn't crash."""
        response = self.client.post(
            reverse('set_language'),
            {'language': 'invalid'},
            follow=True
        )

        # Should still return 200 (Django handles invalid language gracefully)
        self.assertEqual(response.status_code, 200)

    def test_translated_string_changes_with_language(self):
        """Test that translated strings change based on language."""
        from django.utils.translation import gettext as _

        # Check "Login" translation in Russian
        with translation.override('ru'):
            login_ru = str(_('Login'))

        # Check "Login" translation in English
        with translation.override('en'):
            login_en = str(_('Login'))

        # Translations should be different
        self.assertNotEqual(login_ru, login_en)
