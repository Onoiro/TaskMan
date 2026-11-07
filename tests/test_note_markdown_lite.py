"""Tests for the markdown_lite note preview filter."""

from django.template import Context, Template
from django.test import TestCase

from task_manager.notes.markdown_lite import markdown_lite


# ---------------------------------------------------------------------------
# Unit tests for markdown_lite()
# ---------------------------------------------------------------------------


class MarkdownLiteTestCase(TestCase):

    def _eq(self, input_text, expected, **kw):
        kw.setdefault("wrap", False)
        result = markdown_lite(input_text, **kw)
        self.assertHTMLEqual(result, expected)

    # -- Headings --

    def test_h1(self):
        self._eq("# Title",
                 '<strong class="md-lite-h">Title</strong>')

    def test_h2(self):
        self._eq("## Title",
                 '<strong class="md-lite-h">Title</strong>')

    def test_h6(self):
        self._eq("###### Small",
                 '<strong class="md-lite-h">Small</strong>')

    def test_no_headings(self):
        self._eq("## Title", "Title", headings=False)

    def test_multiple_headings(self):
        self._eq("# A\n## B",
                 '<strong class="md-lite-h">A</strong><strong '
                 'class="md-lite-h">B</strong>')

    # -- Bold / Italic / Strikethrough --

    def test_bold(self):
        self._eq("**bold**", "<strong>bold</strong>")

    def test_italic(self):
        self._eq("*italic*", "<em>italic</em>")

    def test_bold_and_italic(self):
        self._eq("**bold** and *italic*",
                 "<strong>bold</strong> and <em>italic</em>")

    def test_strikethrough(self):
        self._eq("~~deleted~~", "<del>deleted</del>")

    # -- Inline code --

    def test_inline_code(self):
        self._eq("`code`", "<code>code</code>")

    def test_inline_code_with_specials(self):
        self._eq("`<tag>`", "<code>&lt;tag&gt;</code>")

    # -- Links --

    def test_link_plain_text(self):
        self._eq("[click](https://example.com)", "click")

    def test_link_with_text(self):
        self._eq("[Google](https://google.com) visit", "Google visit")

    # -- Images --

    def test_image_alt_only(self):
        self._eq("![alt text](img.png)", "alt text")

    def test_image_empty_alt(self):
        self._eq("![](img.png)", "")

    # -- Lists --

    def test_unordered_list(self):
        self._eq("- one\n- two", "\u2022 one \u2022 two")

    def test_task_list_checked(self):
        self._eq("- [x] done", "\u2611 done")

    def test_task_list_unchecked(self):
        self._eq("- [ ] todo", "\u2610 todo")

    def test_task_list_upper_x(self):
        self._eq("- [X] done", "\u2611 done")

    # -- Blockquote --

    def test_blockquote(self):
        self._eq("> quote",
                 '<em class="md-lite-quote">quote</em>')

    # -- Horizontal rule --

    def test_hr(self):
        self._eq("---", "")

    def test_hr_asterisk(self):
        self._eq("***", "")

    # -- Fenced code --

    def test_fenced_code_stripped(self):
        self._eq("```\ncode\n```", "")

    # -- Paragraphs --

    def test_paragraphs(self):
        self._eq("para1\n\npara2", "para1<br><br>para2")

    def test_single_newline(self):
        self._eq("line1\nline2", "line1 line2")

    # -- XSS safety --

    def test_xss_script_tag(self):
        self._eq("<script>alert(1)</script>",
                 "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_xss_img_onerror(self):
        self._eq('<img src=x onerror=alert(1)>',
                 '&lt;img src=x onerror=alert(1)&gt;')

    def test_xss_attribute_in_bold(self):
        self._eq('**<script>bad</script>**',
                 "<strong>&lt;script&gt;bad&lt;/script&gt;</strong>")

    # -- Edge cases --

    def test_empty_string(self):
        self._eq("", "")

    def test_none_input(self):
        self._eq(None, "")

    def test_only_whitespace(self):
        self._eq("   ", "   ")

    def test_mixed_content(self):
        text = (
            "# Note\n\n**bold** and *italic* and `code`.\n\n"
            "- item one\n- [x] item two\n\n"
            "[link](https://x.com)\n\n"
            "> quote"
        )
        result = markdown_lite(text)
        self.assertIn('<strong class="md-lite-h">Note</strong>', result)
        self.assertIn("<strong>bold</strong>", result)
        self.assertIn("<em>italic</em>", result)
        self.assertIn("\u2022 item one", result)
        self.assertIn("\u2611 item two", result)
        self.assertIn("<em class=", result)

    # -- Wrapper span --

    def test_wrap_adds_span(self):
        result = markdown_lite("hello")
        self.assertEqual(
            result, '<span class="md-lite">hello</span>')

    def test_wrap_skipped_for_empty(self):
        self.assertEqual(markdown_lite("   "), "   ")
        self.assertEqual(markdown_lite(""), "")


# ---------------------------------------------------------------------------
# Template filter tests
# ---------------------------------------------------------------------------


class MdLiteFilterTestCase(TestCase):

    def _render(self, tpl, **ctx):
        return Template("{% load note_markdown %}" + tpl).render(
            Context(ctx)
        )

    def test_filter_renders_markup(self):
        out = self._render("{{ text|md_lite }}", text="**hi**")
        self.assertIn("<strong>hi</strong>", out)

    def test_filter_escapes_html(self):
        out = self._render("{{ text|md_lite }}",
                           text="<script>x</script>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_filter_empty(self):
        self.assertEqual(
            self._render("{{ text|md_lite }}", text=""), "")

    def test_filter_none(self):
        self.assertEqual(
            self._render("{{ text|md_lite }}", text=None), "")

    def test_filter_truncates_raw_source(self):
        # Truncation happens before rendering, so HTML tags are
        # never cut in half
        out = self._render("{{ text|md_lite:10 }}",
                           text="**bold text that is long**")
        self.assertNotIn("<strong>", out)  # markers were cut apart
        self.assertTrue(out.rstrip().endswith("\u2026</span>"))

    def test_filter_no_truncation_when_short(self):
        out = self._render("{{ text|md_lite:100 }}", text="**bold**")
        self.assertIn("<strong>bold</strong>", out)
        self.assertNotIn("\u2026", out)

    def test_plain_heading_stripped_without_class(self):
        out = self._render("{{ text|md_lite_plain }}", text="## Title")
        self.assertNotIn("md-lite-h", out)
        self.assertIn("Title", out)
