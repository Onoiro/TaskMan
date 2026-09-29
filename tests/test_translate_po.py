"""Tests for scripts/translate_po.py placeholder handling.

The script used to send ``%(name)s`` to the API as plain text, because
its regex expected the conversion letter before the closing bracket.
Yandex then split or renamed the placeholder and the broken string went
straight into the .mo files. These tests pin the escaping contract, the
marker round trip and the locale directory name mapping.
"""
import contextlib
import io
from unittest import TestCase

from scripts import translate_po as tp


@contextlib.contextmanager
def quiet():
    """Silence the script warnings expected in negative test cases."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


class PlaceholderPatternTestCase(TestCase):
    """The regex must find every placeholder style used in the .po files."""

    def test_named_placeholders_are_found(self):
        found = tp.PLACEHOLDER_RE.findall(
            "Image '%(name)s' is too large, max %(max)s MB."
        )
        self.assertEqual(found, ['%(name)s', '%(max)s'])

    def test_positional_placeholders_are_found(self):
        self.assertEqual(
            tp.PLACEHOLDER_RE.findall('Hello %s and %d'), ['%s', '%d']
        )

    def test_brace_placeholders_are_found(self):
        found = tp.PLACEHOLDER_RE.findall(
            "You have been assigned to task: {task_name}"
        )
        self.assertEqual(found, ['{task_name}'])

    def test_plain_text_has_no_placeholders(self):
        self.assertEqual(
            tp.PLACEHOLDER_RE.findall('Zoom in'), []
        )


class EscapeRestoreTestCase(TestCase):
    """Escaping must be reversible, including for moved markers."""

    def test_round_trip_keeps_placeholders(self):
        source = "Image '%(name)s' has unsupported format."
        escaped, originals = tp.escape_placeholders(source)
        self.assertEqual(originals, ['%(name)s'])
        self.assertNotIn('%(name)s', escaped)
        self.assertEqual(
            tp.restore_placeholders(escaped, originals), source
        )

    def test_brace_placeholder_survives_round_trip(self):
        source = "You have been invited to join team '{team_name}'"
        escaped, originals = tp.escape_placeholders(source)
        self.assertEqual(originals, ['{team_name}'])
        self.assertEqual(
            tp.restore_placeholders(escaped, originals), source
        )

    def test_marker_index_survives_reordering(self):
        """A translator may reorder placeholders between languages."""
        source = '%(username)s joined %(team_name)s'
        escaped, originals = tp.escape_placeholders(source)
        first, second = escaped.split(' joined ')
        reordered = f'{second} joined {first}'
        restored = tp.restore_placeholders(reordered, originals)
        self.assertEqual(restored, '%(team_name)s joined %(username)s')


class VerifyPlaceholdersTestCase(TestCase):
    """Placeholder verification guards the entries written to disk."""

    def test_missing_placeholder_is_detected(self):
        with quiet():
            self.assertFalse(
                tp.verify_placeholders(
                    "Image '%(name)s' is too large.", 'Слишком большой файл.'
                )
            )

    def test_kept_placeholder_passes(self):
        self.assertTrue(
            tp.verify_placeholders(
                "Image '%(name)s' is too large.",
                "Файл '%(name)s' слишком большой.",
            )
        )

    def test_text_without_placeholders_passes(self):
        self.assertTrue(tp.verify_placeholders('Zoom in', 'Увеличить'))


class ApplySingleTranslationTestCase(TestCase):
    """Broken API output must be flagged instead of written to the file."""

    def _entry(self, msgid):
        import polib

        return polib.POEntry(msgid=msgid, msgstr='')

    def test_missing_marker_marks_entry_fuzzy(self):
        entry = self._entry("Image '%(name)s' is too large.")
        with quiet():
            success, needs_fuzzy, msgstr = tp._apply_single_translation(
                entry, 0, 'Файл слишком большой.', [['%(name)s']]
            )
        self.assertFalse(success)
        self.assertTrue(needs_fuzzy)
        self.assertEqual(msgstr, '')

    def test_duplicated_marker_marks_entry_fuzzy(self):
        entry = self._entry("Image '%(name)s' is too large.")
        escaped, originals = tp.escape_placeholders(entry.msgid)
        with quiet():
            success, needs_fuzzy, msgstr = tp._apply_single_translation(
                entry, 0, f'{escaped} {escaped}', [originals]
            )
        self.assertFalse(success)
        self.assertTrue(needs_fuzzy)
        self.assertEqual(msgstr, '')

    def test_valid_translation_is_restored_not_raw(self):
        """The markers must never reach the .po file."""
        entry = self._entry("Image '%(name)s' is too large.")
        escaped, originals = tp.escape_placeholders(entry.msgid)
        success, needs_fuzzy, msgstr = tp._apply_single_translation(
            entry, 0, escaped.replace('Image', 'Файл'), [originals]
        )
        self.assertTrue(success)
        self.assertFalse(needs_fuzzy)
        self.assertEqual(msgstr, "Файл '%(name)s' is too large.")
        self.assertNotIn('__PH', msgstr)

    def test_missing_translation_returns_empty_msgstr(self):
        entry = self._entry('Zoom in')
        with quiet():
            success, needs_fuzzy, msgstr = tp._apply_single_translation(
                entry, 0, None, [[]]
            )
        self.assertFalse(success)
        self.assertFalse(needs_fuzzy)
        self.assertEqual(msgstr, '')


class ApplyTranslationsTestCase(TestCase):
    """Entries written to the file must hold the restored text."""

    def _entry(self, msgid):
        import polib

        return polib.POEntry(msgid=msgid, msgstr='')

    def test_written_msgstr_has_placeholders_restored(self):
        entry = self._entry("Image '%(name)s' is too large.")
        escaped, originals = tp.escape_placeholders(entry.msgid)
        translated, warnings = tp._apply_translations(
            [entry], [originals], [escaped.replace('Image', 'Файл')]
        )
        self.assertEqual(translated, 1)
        self.assertEqual(warnings, 0)
        self.assertEqual(entry.msgstr, "Файл '%(name)s' is too large.")
        self.assertFalse(entry.fuzzy)

    def test_broken_entry_is_left_empty_and_fuzzy(self):
        entry = self._entry("Image '%(name)s' is too large.")
        with quiet():
            translated, warnings = tp._apply_translations(
                [entry], [['%(name)s']], ['Файл слишком большой.']
            )
        self.assertEqual(translated, 0)
        self.assertEqual(warnings, 1)
        self.assertEqual(entry.msgstr, '')
        self.assertTrue(entry.fuzzy)


class AvailableLangsTestCase(TestCase):
    """Locale directory names must be reported as language codes."""

    def test_zh_hans_directory_is_reported_as_code(self):
        self.assertIn('zh-hans', tp._get_available_langs())

    def test_from_ru_targets_match_available_langs(self):
        available = set(tp._get_available_langs())
        matched = [
            lang for lang in tp.FROM_RU_TARGETS if lang in available
        ]
        self.assertEqual(sorted(matched), sorted(tp.FROM_RU_TARGETS))

    def test_default_mode_supports_every_available_language(self):
        """zh_Hans used to slip through and break the API call."""
        for lang in tp._get_available_langs():
            self.assertIn(lang, tp.SUPPORTED_LANG_MAP)
