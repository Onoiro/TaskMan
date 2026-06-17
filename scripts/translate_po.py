#!/usr/bin/env python
"""Translate empty or fuzzy msgid entries in Django .po files.

Scans all language .po files under task_manager/locale/, identifies entries
with empty or fuzzy msgstr, and automatically translates them via the
Yandex Cloud Translate API. Placeholder strings like ``%(name)s`` and ``%d``
are preserved during translation.

By default, translates from English to all target languages except Russian.
Supports two-stage translation workflow:

1. EN -> RU: Developer translates Russian first, reviews and edits manually.
2. RU -> AZ/KY/TG: Uses verified Russian as source for other languages.

Environment variables:

- ``YANDEX_TRANSLATE_API_KEY``: Yandex Cloud API key (required).
- ``YANDEX_FOLDER_ID``: Yandex Cloud folder ID (required).
- ``SKIP_LANGS``: Comma-separated list of languages to skip (default: ru).
- ``TARGET_LANG``: Translate only this language (e.g., ``ru``).
- ``FROM_RU=1``: Use Russian as source language for az/ky/tg translation.
- ``DRY_RUN=1``: Show what would be translated without API calls.

Usage::

    # Default: translate all except Russian (EN -> AZ/KY/TG)
    poetry run python scripts/translate_po.py

    # Translate only Russian (EN -> RU)
    TARGET_LANG=ru poetry run python scripts/translate_po.py

    # Translate AZ/KY/TG from verified Russian (RU -> target)
    FROM_RU=1 poetry run python scripts/translate_po.py

    # Dry run: preview without API calls
    DRY_RUN=1 poetry run python scripts/translate_po.py

    # List untranslated entries
    poetry run python scripts/translate_po.py list-ru
    poetry run python scripts/translate_po.py list
"""

import json
import os
import re
import sys
from pathlib import Path

import polib
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

YANDEX_API_KEY = os.environ.get("YANDEX_TRANSLATE_API_KEY", "")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID", "")
SKIP_LANGS = [
    lang.strip()
    for lang in os.environ.get("SKIP_LANGS", "").split(",")
    if lang.strip()
]
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
TARGET_LANG = os.environ.get("TARGET_LANG", "").strip()
FROM_RU = os.environ.get("FROM_RU", "0") == "1"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCALE_DIR = PROJECT_ROOT / "task_manager" / "locale"
API_URL = (
    "https://translate.api.cloud.yandex.net/translate/v2/translate"
)
CHUNK_SIZE = 100

# Supported language pairs for en -> target translation.
# Mapped from language code to Yandex language code (e.g. ru -> ru).
SUPPORTED_LANG_MAP = {
    "ru": "ru",
    "az": "az",
    "ky": "ky",
    "tg": "tg",
}

# Languages to translate when FROM_RU=1 (source is always ru).
FROM_RU_TARGETS = ["az", "ky", "tg"]

# ---------------------------------------------------------------------------
# Placeholder helpers
# ---------------------------------------------------------------------------

# Pattern matches: %(name)s, %(count)d, %s, %d
PLACEHOLDER_RE = re.compile(
    r"%\([^)]+?[sd]\)"
    r"|"
    r"%(?=[sd])"
)

_PLACEHOLDER_COUNTER = 0


def _reset_counter():
    """Reset the placeholder counter for a new batch."""
    global _PLACEHOLDER_COUNTER
    _PLACEHOLDER_COUNTER = 0


def _placeholder_replacer(match):
    """Return a unique marker for each matched placeholder."""
    global _PLACEHOLDER_COUNTER
    _PLACEHOLDER_COUNTER += 1
    return f"__PH{_PLACEHOLDER_COUNTER - 1:04d}__"


def escape_placeholders(text):
    """Replace all Django-style placeholders with unique markers.

    Args:
        text: Source string that may contain ``%(name)s``, ``%d``, etc.

    Returns:
        Tuple of (escaped_string, list_of_original_placeholders).
    """
    _reset_counter()
    originals = PLACEHOLDER_RE.findall(text)
    escaped = PLACEHOLDER_RE.sub(_placeholder_replacer, text)
    return escaped, originals


def restore_placeholders(text, originals):
    """Restore original placeholder tokens into an escaped string.

    Args:
        text: String containing ``__PH0000__`` markers.
        originals: List of the original placeholder strings (in order).

    Returns:
        String with markers replaced by their originals.
    """
    counter = 0

    def _repl(m):
        nonlocal counter
        idx = counter
        counter += 1
        if idx < len(originals):
            return originals[idx]
        return m.group(0)

    return PLACEHOLDER_RE.sub(_repl, text)


def verify_placeholders(original, translated):
    """Check that every placeholder from original is in translated.

    Args:
        original: The original msgid string.
        translated: The translated string from the API.

    Returns:
        True if all placeholders are preserved, False otherwise.
    """
    found = PLACEHOLDER_RE.findall(original)
    if not found:
        return True

    missing = set()
    for ph in found:
        orig_count = original.count(ph)
        trans_count = translated.count(ph)
        if trans_count < orig_count:
            missing.add(ph)

    if missing:
        msg = f"placeholders missing: {', '.join(sorted(missing))}"
        print(f"  WARNING: {msg}")
        return False
    return True


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _http_request(url, method="GET", headers=None, data=None):
    """Send an HTTP request using ``urllib.request``.

    Args:
        url: Request URL.
        method: HTTP method (GET, POST, etc.).
        headers: Dict of HTTP headers.
        data: Dict of JSON body data (for POST/PUT).

    Returns:
        Parsed JSON response as a dict.
    """
    import urllib.error
    import urllib.request

    req_headers = headers or {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    else:
        body = None

    req = urllib.request.Request(
        url, data=body, headers=req_headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        print(f"\n  ERROR HTTP {exc.code}: {body_text[:200]}")
        raise
    except urllib.error.URLError as exc:
        print(f"\n  ERROR: {exc.reason}")
        raise


def is_language_supported(lang_code, supported_codes):
    """Check whether lang_code is supported for en->lang translation.

    Args:
        lang_code: Target language code, e.g. ``"ru"``.
        supported_codes: Set of supported language codes.

    Returns:
        True if lang_code is in the supported set.
    """
    return lang_code in supported_codes


def translate_texts(texts, target_lang, supported_codes, source_lang="en"):
    """Translate a list of texts to target_lang.

    Splits texts into chunks of up to 100 and sends each chunk to the API.

    Args:
        texts: List of strings to translate.
        target_lang: Target language code, e.g. ``"ru"``.
        supported_codes: Set of supported language codes.
        source_lang: Source language code (``"en"`` or ``"ru"``).

    Returns:
        List of translated strings (same length as texts).
    """
    yandex_target = SUPPORTED_LANG_MAP.get(target_lang)
    if not yandex_target:
        print(f"  ERROR: language {target_lang} not supported by API.")
        return [None] * len(texts)

    translations = []
    total_chunks = (len(texts) + CHUNK_SIZE - 1) // CHUNK_SIZE

    for i in range(0, len(texts), CHUNK_SIZE):
        chunk_idx = i // CHUNK_SIZE + 1
        chunk = texts[i: i + CHUNK_SIZE]
        print(
            f"  Chunk {chunk_idx}/{total_chunks}: "
            f"translating {len(chunk)} texts -> {target_lang}"
        )

        payload = {
            "folderId": YANDEX_FOLDER_ID,
            "texts": chunk,
            "sourceLanguageCode": source_lang,
            "targetLanguageCode": yandex_target,
        }
        headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}"}
        resp = _http_request(API_URL, method="POST", headers=headers,
                             data=payload)

        for item in resp.get("translations", []):
            translations.append(item.get("text", ""))

    # Fill in missing translations
    while len(translations) < len(texts):
        translations.append(None)

    return translations


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def collect_entries(pob):
    """Collect entries with empty or fuzzy msgstr.

    Skips obsolete entries.

    Args:
        pob: A ``polib.POFile`` instance.

    Returns:
        List of ``(entry, index)`` tuples.
    """
    results = []
    for idx, entry in enumerate(pob):
        if entry.obsolete:
            continue
        msgstr = entry.msgstr or entry.msgstr_plural.get(0, "")
        if not msgstr or entry.fuzzy:
            results.append((entry, idx))
    return results


def _apply_single_translation(entry, i, translated_raw, originals):
    """Apply one translated text to a PO entry.

    Restores placeholders, verifies them, and sets msgstr/fuzzy flags.

    Args:
        entry: The polib PO entry to update.
        i: Entry index (for logging).
        translated_raw: Raw translation from the API.
        originals: Original placeholder list.

    Returns:
        Tuple (success, needs_fuzzy).
        success=False means API returned no translation.
        needs_fuzzy=True means placeholders didn't match.
    """
    if translated_raw is None:
        print(
            f"  WARNING: no translation for entry {i + 1}. "
            "Marking fuzzy."
        )
        return False, False

    ph_list = originals[i]
    translated = restore_placeholders(translated_raw, ph_list)

    if not verify_placeholders(entry.msgid, translated):
        print(
            f"  WARNING: entry {i + 1} — placeholders mismatch. "
            "Marking fuzzy."
        )
        return False, True

    return True, False


def _write_back(pob, po_path):
    """Save the PO file to disk.

    Args:
        pob: The polib POFile to save.
        po_path: Path to write the file to.
    """
    print(f"  Saving {po_path} ...")
    pob.save(str(po_path))


def build_russian_translation_dict():
    """Build a dictionary mapping msgid -> Russian msgstr.

    Reads ru/django.po and returns a dict of msgid (newline-joined) -> msgstr
    for all non-obsolete, non-empty entries.

    Returns:
        Dict mapping msgid strings to their Russian translations.
    """
    ru_po_path = LOCALE_DIR / "ru" / "LC_MESSAGES" / "django.po"
    if not ru_po_path.exists():
        print("  WARNING: ru/django.po not found. FROM_RU mode disabled.")
        return {}

    pob = polib.pofile(str(ru_po_path))
    ru_dict = {}

    for entry in pob:
        if entry.obsolete:
            continue
        msgstr = entry.msgstr or entry.msgstr_plural.get(0, "")
        if not msgstr:
            continue
        msgid = entry.msgid.replace("\n", " ")
        ru_dict[msgid] = msgstr

    print(f"  Built Russian translation dictionary: {len(ru_dict)} entries.")
    return ru_dict


def _check_po_prerequisites(lang_code, pob, entries, supported_codes):
    """Check prerequisites and return early if nothing to do.

    Checks file existence, empty entries, dry-run mode,
    and language support. Returns True if processing should continue.

    Args:
        lang_code: Language code, e.g. ``"ru"``.
        pob: The polib POFile instance.
        entries: List of entries needing translation.
        supported_codes: Set of supported language codes.

    Returns:
        True if processing should continue, False otherwise.
    """
    if not entries:
        print(f"  No empty/fuzzy entries in {lang_code}.")
        return False

    print(f"  Found {len(entries)} entries needing translation.")

    if DRY_RUN:
        print("  DRY_RUN=1 — skipping API calls and file writes.")
        for entry, _ in entries:
            msgid = entry.msgid.replace("\n", " ")
            print(f"    msgid: {msgid[:100]}")
        return False

    if not is_language_supported(lang_code, supported_codes):
        print(
            f"  WARNING: language {lang_code} not supported "
            "by Yandex API. Skipping."
        )
        return False

    return True


def process_po_file(lang_code, supported_codes, ru_dict=None):
    """Process a single .po file.

    Translates empty/fuzzy entries, verifies placeholders,
    and writes the file back.

    Args:
        lang_code: Language code, e.g. ``"ru"``.
        supported_codes: Cached set of supported language pairs.
        ru_dict: Optional dict of msgid -> Russian translation (for FROM_RU).

    Returns:
        Dict with counts: ``{"translated": N, "skipped_warnings": M}``.
    """
    po_path = (
        LOCALE_DIR / lang_code
        / "LC_MESSAGES" / "django.po"
    )
    if not po_path.exists():
        return {"translated": 0, "skipped_warnings": 0}

    print(f"\nProcessing {lang_code}: {po_path}")

    pob = polib.pofile(str(po_path))
    entries = collect_entries(pob)

    if not _check_po_prerequisites(
        lang_code, pob, entries, supported_codes
    ):
        return {"translated": 0, "skipped_warnings": 0}

    # Prepare texts for translation
    texts, originals, entry_indices = _build_translation_batch(entries)

    # Determine source language and translations
    if ru_dict and lang_code in FROM_RU_TARGETS:
        # FROM_RU mode: use Russian as source
        translated_texts, skipped_count = (
            _translate_from_russian(
                entry_indices, ru_dict, lang_code, supported_codes
            )
        )
    else:
        # Default EN mode
        translated_texts = translate_texts(
            texts, lang_code, supported_codes
        )
        skipped_count = 0

    # Write back results
    translated_count, warning_count = _apply_translations(
        entry_indices, originals, translated_texts
    )

    # Save file
    _write_back(pob, po_path)

    print(
        f"  Done: {translated_count} translated, "
        f"{warning_count} skipped with warnings."
    )
    if skipped_count:
        print(f"  Skipped (no Russian): {skipped_count}")

    return {
        "translated": translated_count,
        "skipped_warnings": warning_count,
        "skipped_no_ru": skipped_count,
    }


def _build_from_ru_batch(entry_indices, ru_dict):
    """Prepare texts for FROM_RU translation and count skipped.

    Args:
        entry_indices: List of PO entries to translate.
        ru_dict: Dict of msgid -> Russian msgstr.

    Returns:
        Tuple of (texts, originals, skipped_count).
    """
    texts = []
    originals = []
    skipped_count = 0

    for entry in entry_indices:
        msgid = entry.msgid.replace("\n", " ")
        ru_translation = ru_dict.get(msgid, "").strip()

        if not ru_translation:
            skipped_count += 1
            continue

        escaped, ph_list = escape_placeholders(ru_translation)
        texts.append(escaped)
        originals.append(ph_list)

    return texts, originals, skipped_count


def _translate_from_russian(entry_indices, ru_dict,
                            target_lang, supported_codes):
    """Translate entries using Russian as the source language.

    For each entry, looks up the msgid in the Russian dictionary.
    If a Russian translation is found, uses it as source for Yandex API.
    If not found, marks the entry as skipped.

    Args:
        entry_indices: List of PO entries to translate.
        ru_dict: Dict of msgid -> Russian msgstr.
        target_lang: Target language code (az, ky, or tg).
        supported_codes: Set of supported codes.

    Returns:
        Tuple of (translated_texts, skipped_count).
    """
    texts, originals, skipped_count = _build_from_ru_batch(
        entry_indices, ru_dict
    )

    if not texts:
        print(
            f"  No Russian translations found for {target_lang}. "
            "Skipping API call."
        )
        return [None] * len(entry_indices), skipped_count

    translated_texts = translate_texts(
        texts, target_lang, supported_codes, source_lang="ru"
    )

    # Build result aligned with entry_indices
    result = []
    text_idx = 0
    for entry in entry_indices:
        msgid = entry.msgid.replace("\n", " ")
        ru_translation = ru_dict.get(msgid, "").strip()
        if not ru_translation:
            result.append(None)
        elif text_idx < len(translated_texts):
            result.append(translated_texts[text_idx])
            text_idx += 1
        else:
            result.append(None)

    return result, skipped_count


def _build_translation_batch(entries):
    """Build parallel lists for the translation API call.

    Args:
        entries: List of (entry, index) from collect_entries.

    Returns:
        Tuple of (texts, originals, entry_indices) lists.
    """
    texts = []
    originals = []
    entry_indices = []

    for entry, _ in entries:
        msgid = entry.msgid.replace("\n", " ")
        escaped, ph_list = escape_placeholders(msgid)
        texts.append(escaped)
        originals.append(ph_list)
        entry_indices.append(entry)

    return texts, originals, entry_indices


def _apply_translations(entry_indices, originals, translated_texts):
    """Apply translated texts back to PO entries.

    Args:
        entry_indices: List of PO entries.
        originals: List of placeholder lists.
        translated_texts: List of raw translations from the API.

    Returns:
        Tuple of (translated_count, warning_count).
    """
    translated_count = 0
    warning_count = 0

    for i, entry in enumerate(entry_indices):
        success, needs_fuzzy = _apply_single_translation(
            entry, i, translated_texts[i], originals
        )

        if not success:
            warning_count += 1
            continue

        if needs_fuzzy:
            entry.fuzzy = True
            entry.msgstr = ""
            warning_count += 1
            continue

        entry.msgstr = translated_texts[i]
        entry.fuzzy = False
        translated_count += 1

    return translated_count, warning_count


def _resolve_target_langs(available_langs):
    """Determine which languages to process based on env vars.

    Args:
        available_langs: Sorted list of available language codes.

    Returns:
        Tuple of (target_langs, ru_dict_or_None).
    """
    ru_dict = None

    if TARGET_LANG:
        # Single language mode (e.g. TARGET_LANG=ru)
        if TARGET_LANG not in available_langs:
            print(
                f"  WARNING: language '{TARGET_LANG}' not found in "
                f"{', '.join(available_langs)}. Nothing to do."
            )
            return [], None
        return [TARGET_LANG], None

    if FROM_RU:
        # FROM_RU mode: translate az/ky/tg from Russian
        target_langs = [
            lang for lang in FROM_RU_TARGETS if lang in available_langs
        ]
        ru_dict = build_russian_translation_dict()
        if not ru_dict:
            print("ERROR: Cannot build Russian dictionary. Aborting.")
            sys.exit(1)
        print("FROM_RU mode: translating az/ky/tg from Russian.")
        return target_langs, ru_dict

    # Default mode: translate all available languages
    target_langs = [
        lang for lang in available_langs if lang not in SKIP_LANGS
    ]
    return target_langs, ru_dict


def _collect_skipped_ids(target_langs, ru_dict):
    """Collect msgids that were skipped due to missing Russian translations.

    Args:
        target_langs: List of target language codes.
        ru_dict: Dict of msgid -> Russian msgstr.

    Returns:
        List of (lang, msgid) tuples.
    """
    all_skipped = []
    for lang in target_langs:
        po_path = LOCALE_DIR / lang / "LC_MESSAGES" / "django.po"
        pob = polib.pofile(str(po_path))
        entries = collect_entries(pob)
        for entry, _ in entries:
            msgid = entry.msgid.replace("\n", " ")
            if ru_dict and ru_dict.get(msgid, "").strip():
                continue
            all_skipped.append((lang, msgid[:120]))
    return all_skipped


def _print_skipped_summary(skipped_ids):
    """Print skipped msgids to stderr with instructions.

    Args:
        skipped_ids: List of (lang, msgid) tuples.
    """
    print(
        f"\n  Skipped (no Russian translation): "
        f"{len(skipped_ids)}"
    )
    print("  These msgids need to be added to ru/django.po first:")
    print("  " + "-" * 56)
    seen = set()
    for lang, msgid in skipped_ids:
        if msgid not in seen:
            print(f"    [{lang}] {msgid}")
            seen.add(msgid)
    print("  " + "-" * 56)
    print("  Run 'make translate-ru' first to add these to Russian,")
    print("  then re-run 'make translate-from-ru'.")


def _validate_config():
    """Validate Yandex API configuration.

    Exits if YANDEX_TRANSLATE_API_KEY or YANDEX_FOLDER_ID is not set.
    """
    if not YANDEX_API_KEY:
        print("ERROR: YANDEX_TRANSLATE_API_KEY is not set.")
        sys.exit(1)
    if not YANDEX_FOLDER_ID:
        print("ERROR: YANDEX_FOLDER_ID is not set.")
        sys.exit(1)


def _get_available_langs():
    """Get sorted list of available language codes.

    Returns:
        List of language codes that have a django.po file.
    """
    return sorted(
        d.name
        for d in LOCALE_DIR.iterdir()
        if d.is_dir()
        and (d / "LC_MESSAGES" / "django.po").exists()
    )


def _process_languages(target_langs, supported_codes, ru_dict):
    """Process all target languages and return totals.

    Args:
        target_langs: List of language codes to process.
        supported_codes: Set of supported language codes.
        ru_dict: Optional Russian dictionary for FROM_RU mode.

    Returns:
        Tuple of (total_translated, total_warnings).
    """
    total_translated = 0
    total_warnings = 0

    for lang in target_langs:
        result = process_po_file(lang, supported_codes, ru_dict=ru_dict)
        total_translated += result.get("translated", 0)
        total_warnings += result.get("skipped_warnings", 0)

    return total_translated, total_warnings


def _run_translation_flow():
    """Run the full translation flow: fetch languages, process each .po file."""
    print("=" * 60)
    print("Django .po Auto-Translator")
    print("=" * 60)

    _validate_config()

    if DRY_RUN:
        print(
            "DRY_RUN=1 — no API calls or file "
            "writes will be performed."
        )
        supported_codes = set()
    else:
        supported_codes = set(SUPPORTED_LANG_MAP.keys())

    available_langs = _get_available_langs()
    target_langs, ru_dict = _resolve_target_langs(available_langs)

    if not target_langs:
        print(
            f"All languages are skipped "
            f"({', '.join(SKIP_LANGS)}). Nothing to do."
        )
        return

    print(f"Target languages: {', '.join(target_langs)}")
    print(f"Skipped languages: {', '.join(SKIP_LANGS)}")

    total_translated, total_warnings = _process_languages(
        target_langs, supported_codes, ru_dict
    )

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Total translated: {total_translated}")
    print(f"  Skipped (warnings): {total_warnings}")

    if FROM_RU:
        all_skipped = _collect_skipped_ids(target_langs, ru_dict)
        if all_skipped:
            _print_skipped_summary(all_skipped)

    print("=" * 60)


# ---------------------------------------------------------------------------
# List untranslated entries
# ---------------------------------------------------------------------------

def show_untranslated(lang_code):
    """Show untranslated entries with line numbers for a given language.

    Reads the .po file and prints each entry with empty or fuzzy msgstr,
    along with its line number in the file.

    Args:
        lang_code: Language code, e.g. ``"ru"``.
    """
    po_path = (
        LOCALE_DIR / lang_code
        / "LC_MESSAGES" / "django.po"
    )
    if not po_path.exists():
        print(f"File not found: {po_path}")
        sys.exit(1)

    print(f"Untranslated entries in {lang_code}:")
    print("-" * 60)

    pob = polib.pofile(str(po_path))
    count = 0

    for entry in pob:
        if entry.obsolete:
            continue
        msgstr = entry.msgstr or entry.msgstr_plural.get(0, "")
        if not msgstr or entry.fuzzy:
            msgid = entry.msgid.replace("\n", " ")[:120]
            print(f"{entry.linenum}: {msgid}")
            count += 1

    print("-" * 60)
    print(f"Total: {count} entries")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point: dispatch subcommands."""
    command = sys.argv[1] if len(sys.argv) > 1 else "translate"

    if command == "list-ru":
        show_untranslated("ru")
        return

    if command == "list":
        available_langs = sorted(
            d.name
            for d in LOCALE_DIR.iterdir()
            if d.is_dir()
            and (d / "LC_MESSAGES" / "django.po").exists()
        )
        for lang in available_langs:
            show_untranslated(lang)
            print()
        return

    # Default: full translation flow
    _run_translation_flow()


if __name__ == "__main__":
    main()
