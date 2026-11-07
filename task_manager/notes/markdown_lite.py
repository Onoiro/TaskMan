"""
markdown_lite — minimal markdown -> HTML for note list previews.

Rendered subset (safe, closed list of tags):
  # ... ######  -> <strong class="md-lite-h"> (optional)
  **bold**      -> <strong>
  *italic*      -> <em>
  ~~strike~~    -> <del>
  `code`        -> <code>
  - item        -> bullet
  - [x] / [ ]   -> checked / unchecked box
  > quote       -> <em class="md-lite-quote">
  [text](url)   -> text (no <a>: cards use stretched-link)

Everything else (images, fenced code, hr) is stripped to plain text.
Input is HTML-escaped BEFORE any substitution, so raw HTML can never
reach the output. This keeps the filter XSS-safe without bleach.
"""

import re

from django.utils.html import escape


def _task_list_item(match):
    """Replace a GFM task list marker with a checkbox glyph."""
    checked = match.group(1).lower() == 'x'
    return "\u2611 " if checked else "\u2610 "


def markdown_lite(text, headings=True, wrap=True):
    """Return *text* with a minimal Markdown subset rendered to HTML.

    headings=False strips heading markers without adding a class
    (used for card pseudo-titles that are already styled as headings).
    wrap=False returns the fragment without the .md-lite span wrapper.
    """
    text = escape(text or "")

    # Fenced code blocks are removed first so their content does not
    # interfere with inline rules
    text = re.sub(r"```[\s\S]*?```", "", text)

    # Horizontal rules (must be before inline bold/italic)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # Headings: keep the text, drop the hashes
    if headings:
        text = re.sub(
            r"^(#{1,6})\s+(.+)$",
            lambda m: f'<strong class="md-lite-h">{m.group(2)}</strong>',
            text,
            flags=re.MULTILINE,
        )
    else:
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Task list items before plain list markers
    text = re.sub(
        r"^\s*[-*+]\s+\[([ xX])\]\s+",
        _task_list_item,
        text,
        flags=re.MULTILINE,
    )

    # Unordered list markers -> bullet glyph
    text = re.sub(r"^\s*[-*+]\s+", "\u2022 ", text, flags=re.MULTILINE)

    # Blockquotes: ">" is already escaped to "&gt;"
    text = re.sub(
        r"^&gt;\s*(.*)$",
        r'<em class="md-lite-quote">\1</em>',
        text,
        flags=re.MULTILINE,
    )

    # Images -> alt text only
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)

    # Links -> anchor text only
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)

    # Inline emphasis (bold before italic)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
    text = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", text)

    # Paragraph breaks -> <br>, single newlines -> space (breaks: true)
    text = re.sub(r"\n\s*\n", "<br><br>", text)
    text = re.sub(r"\s*\n\s*", " ", text)

    if not text.strip():
        return text
    if wrap:
        return f'<span class="md-lite">{text}</span>'
    return text
