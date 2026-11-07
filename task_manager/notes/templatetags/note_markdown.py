from django import template
from django.utils.safestring import mark_safe

from task_manager.notes.markdown_lite import markdown_lite

register = template.Library()

ELLIPSIS = "\u2026"


def _truncate(text, length):
    """Truncate raw markdown before rendering.

    truncatechars must not run after markdown_lite: it would cut HTML
    tags in half and re-escape the safe output. Truncating the raw
    source may split markdown syntax, which is harmless (the regex
    just does not match).
    """
    if length and len(text) > length:
        return text[: length - 1] + ELLIPSIS
    return text


def _render(value, length, headings):
    if not value:
        return ""
    text = _truncate(str(value), length)
    # Output is safe: markdown_lite escapes all input before tagging
    return mark_safe(markdown_lite(text, headings=headings))


@register.filter(name="md_lite")
def md_lite(value, length=None):
    """Render a minimal Markdown subset to safe HTML for list previews."""
    return _render(value, length, headings=True)


@register.filter(name="md_lite_plain")
def md_lite_plain(value, length=None):
    """Same as md_lite but heading markers are only stripped.

    Used for card pseudo-titles that are already styled as headings,
    so an extra bold heading class would double the emphasis.
    """
    return _render(value, length, headings=False)
